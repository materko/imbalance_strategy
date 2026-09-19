"""Výpočet na hube (`--remote`): zadanie, čakanie a vyzdvihnutie výsledku, dávky mriežky."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from tradebot.core.env import getenv

from .common import api, server_alive


def _webapp_hub_ready(url: str) -> bool:
    """Beží webapp a má agenta hubu? Stará webapp bez `/api/hub` (404) znamená nie."""
    if not server_alive(url):
        return False
    try:
        return bool((api(url, "/api/hub") or {}).get("configured"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return False


#: Dopredu zadané výpočty mriežky: odtlačok (params, settings, note) → id výpočtu na hube.
#: `_remote_prefetch` ich zadá naraz, `_remote_execute` si potom každý len vyzdvihne.
_REMOTE_BATCH: dict[str, str] = {}


_REMOTE_WARNED: set[str] = set()


def _batch_key(params: dict, settings: dict, note: str) -> str:
    import hashlib

    blob = json.dumps({"p": params, "s": settings, "n": note}, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _remote_client(args: argparse.Namespace):
    """(config agenta, klient hubu); SystemExit, keď agent nie je nastavený alebo nesmie posielať."""
    from ...hub import config as hub_config
    from ...hub.client import HubClient

    cfg = hub_config.load()
    if cfg is None:
        raise SystemExit("agent nie je nastaveny: python -m tester.hub setup --name … --hub-url … --token …")
    try:
        return cfg, HubClient.from_config(cfg)
    except PermissionError as exc:
        raise SystemExit(str(exc))


def _remote_submit(args: argparse.Namespace, params: dict, settings: dict, note: str,
                   quiet: bool = False, *, queue: bool | None = None) -> dict:
    """Zadá jeden výpočet na hub a vráti jeho záznam (stav `assigned` alebo `queued`).

    Zadanie ide cez bežiacu webapp, keď je (jej agent si zapíše, čo poslal, a výsledok
    vyzdvihne aj keď toto CLI medzitým skončí); inak priamo na hub.
    """
    from ...hub import config as hub_config, gitcode, protocol as P
    from ...hub.client import NoCapacityError, fmt_eta
    from ..store import RunStore

    cfg, client = _remote_client(args)
    user = args.user or getenv("USER") or ""
    kind = P.kind_of(settings)
    cores: int | str | None = None
    if getattr(args, "cores", None):
        cores = P.ALL if args.cores == P.ALL else int(args.cores)
    demand = cores if cores is not None else P.cores_for(settings, kind)
    odhad = P.estimate_seconds(settings, RunStore().all(), cores=os.cpu_count() or 1)
    max_wait = args.max_wait * 60 if getattr(args, "max_wait", None) else None
    max_seconds = args.max_runtime * 60 if getattr(args, "max_runtime", None) else None
    if queue is None:
        queue = bool(getattr(args, "queue", False))

    # Agent počíta na commite zadávateľa (pullne si ho, keď ho nemá) — necommitnuté zmeny
    # kódu k nemu nedôjdu, takže by beh ticho počítal niečo iné, než vidí tester.
    verzia = gitcode.version()
    spinave = gitcode.dirty_code()
    if spinave and "dirty" not in _REMOTE_WARNED:
        _REMOTE_WARNED.add("dirty")
        print(f"POZOR: necommitnute zmeny kodu ({', '.join(spinave[:3])}"
              f"{', …' if len(spinave) > 3 else ''}) — agent pocita commit {verzia or '?'}, "
              f"nie tvoj pracovny strom", file=sys.stderr)
    if not quiet:
        cap = client.capacity(demand)
        print(f"hub {cfg.hub_url}: volni agenti {', '.join(cap['free']) or 'ziadni'}; "
              f"najskorsi start {fmt_eta(cap['eta_start_seconds'])}; vo fronte {cap['queued']}; "
              f"odhad behu {fmt_eta(odhad)}; kod {verzia or '?'}", flush=True)
    payload = {"params": params, "settings": settings, "note": note, "user": user or None}
    telo = {"kind": kind, "payload": payload, "cores": cores, "queue": bool(queue),
            "max_wait_seconds": max_wait, "estimate_seconds": odhad, "note": note,
            "version": verzia or None, "max_seconds": max_seconds}
    try:
        if _webapp_hub_ready(args.url):
            job = api(args.url, "/api/hub/jobs", telo)
        else:
            job = client.submit(kind, payload, cores=cores, queue=bool(queue),
                                max_wait_seconds=max_wait, estimate_seconds=odhad, note=note,
                                version=verzia or None, max_seconds=max_seconds)
            stav = hub_config.load_state()
            stav.sent[job["id"]] = {"kind": kind, "note": note, "created": job.get("created"),
                                    "status": job.get("status"), "run_ids": [], "error": None}
            hub_config.save_state(stav)
    except NoCapacityError as exc:
        raise SystemExit(f"hub odmietol vypocet: {exc.detail.get('message') if isinstance(exc.detail, dict) else exc.detail}\n"
                         f"  najskorsi start: {fmt_eta(exc.eta_start)}; skus --queue (pripadne --max-wait MIN)")
    except urllib.error.HTTPError as exc:
        telo_chyby = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"webapp odmietla vypocet cez hub: {telo_chyby}")
    return job


def _remote_wait(args: argparse.Namespace, job_id: str, settings: dict, quiet: bool = False) -> dict:
    """Počká na výpočet a vráti záznam behu z lokálnej histórie (po vyzdvihnutí zipu)."""
    from ...hub import gitcode
    from ...hub.client import fmt_eta
    from ..store import RunStore

    _, client = _remote_client(args)
    store = RunStore()
    verzia = gitcode.version()

    def tick(j: dict) -> None:
        if quiet:
            return
        if j.get("status") in ("done", "failed") and j.get("agent_version") \
                and j["agent_version"] != verzia:
            print(f"  POZOR: agent {j.get('agent')} pocital na commite {j['agent_version']}, "
                  f"zadany bol {verzia}", flush=True)
        postup = f"{100 * j['progress']:.0f} %" if j.get("progress") is not None else "-"
        if j.get("eta_seconds") is not None:
            zostava = fmt_eta(j["eta_seconds"])
        else:
            zostava = "~" + fmt_eta(j.get("estimate_seconds")) if j.get("estimate_seconds") else "-"
        print(f"  … {j['status']}  agent {j.get('agent') or '-'}  postup {postup}  "
              f"zostava {zostava}", flush=True)

    job = client.wait(job_id, on_tick=tick)
    run_ids = client.collect(job["id"], store.root)
    if job["status"] != "done":
        return {"id": run_ids[0] if run_ids else job["id"], "status": job["status"],
                "error": job.get("error") or f"vypocet skoncil ako {job['status']}", "settings": settings}
    if not run_ids:
        raise SystemExit(f"vypocet {job['id']} skoncil, ale bez behov v historii")
    hlavny = job.get("run_id") if job.get("run_id") in run_ids else run_ids[0]
    return store.get(hlavny) or {"id": hlavny, "status": "failed", "error": "beh sa nepodarilo precitat",
                                 "settings": settings}


def _remote_prefetch(args: argparse.Namespace, items: list[tuple[dict, dict, str]]) -> None:
    """Mriežka na hub **naraz**: všetky body sa zadajú hneď (s frontou), počítajú sa
    paralelne na toľkých agentoch, koľko je voľných, a slučka príkazu si ich už len
    vyzdvihuje v poradí. Bez `--remote` nerobí nič a slučka beží lokálne ako doteraz."""
    if not getattr(args, "remote", False) or len(items) < 2:
        return
    from ...hub.client import fmt_eta

    cfg, client = _remote_client(args)
    cap = client.capacity(1)
    print(f"hub {cfg.hub_url}: {len(items)} vypoctov naraz; volni agenti "
          f"{', '.join(cap['free']) or 'ziadni'} z {cap['online']} online; vo fronte {cap['queued']}; "
          f"najskorsi start {fmt_eta(cap['eta_start_seconds'])}", flush=True)
    ids = []
    for params, settings, note in items:
        job = _remote_submit(args, params, settings, note, quiet=True, queue=True)
        _REMOTE_BATCH[_batch_key(params, settings, note)] = job["id"]
        ids.append(job["id"])
    print(f"  zadane: {', '.join(ids[:6])}{' …' if len(ids) > 6 else ''}")
    print("  (po Ctrl+C vypocty na hube bezia dalej: python -m tester.hub jobs, cancel <id>)\n",
          flush=True)


def _remote_execute(args: argparse.Namespace, params: dict, settings: dict, note: str,
                    quiet: bool = False) -> dict:
    """Beh cez hub (`tester.hub`): kapacita → zadanie → čakanie → výsledok do tejto histórie.

    Čakanie a vyzdvihnutie ide vždy priamo na hub — `collect` je idempotentné, takže je
    jedno, či zip stiahne toto CLI alebo agent bežiacej webapp. Bod mriežky, ktorý už
    zadal `_remote_prefetch`, sa znova nezadáva.
    """
    job_id = _REMOTE_BATCH.pop(_batch_key(params, settings, note), None)
    if job_id is None:
        job = _remote_submit(args, params, settings, note, quiet)
        if not quiet:
            print(f"zadane na hub: {job['id']}  stav {job['status']}"
                  + (f", agent {job['agent']}" if job.get("agent") else ""), flush=True)
        if getattr(args, "no_wait", False):
            return {"id": job["id"], "status": "queued", "settings": settings}
        job_id = job["id"]
    return _remote_wait(args, job_id, settings, quiet)
