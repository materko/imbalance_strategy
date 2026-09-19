"""Hyperopt a jeho história (`hyperopt`, `hyperopts`)."""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from tradebot.core.env import getenv

from .common import _progress_text, api, server_alive, warn_parity
from .remote import _remote_execute, _remote_prefetch
from .run import _execute, _prepare


def cmd_hyperopt(args: argparse.Namespace) -> int:
    """Hyperopt na tom istom zadaní ako sweep, plus overenie na ďalších oknách.

    Beh ide tou istou cestou ako vo webapp: keď webapp beží, zaradí sa do jej fronty
    (`POST /api/hyperopts`), inak ho odohrá lokálny runner. Záznam v histórii, epochy,
    víťaz aj overovacie behy na referenčných oknách tak vznikajú **jedným kódom**
    (`runner._run_hyperopt`), nie kópiou v CLI.
    """
    from ... import engines, hyperopt as ho, sweep as sweep_mod
    from ..store import RunStore

    params, settings = _prepare(args)
    # Rovnaká kontrola ako vo webapp: s peňaženkou menšou než jeden kontrakt má každá
    # epocha nula obchodov a hyperopt beží zbytočne.
    from ... import matrix as mx

    male = mx.wallet_check([settings["pair"]], float(settings.get("wallet") or 0),
                           timeframe=settings.get("timeframe") or "3m",
                           timerange=settings["timerange"])
    if male:
        nominal = male[settings["pair"]]
        cislo = lambda v: f"{v:,.0f}".replace(",", " ")  # noqa: E731
        raise SystemExit(
            f"penazenka {cislo(float(settings.get('wallet') or 0))} je na {settings['pair']} "
            f"mala: jeden kontrakt ~{cislo(nominal)}, kazdy vstup by bol odmietnuty a vsetky "
            f"epochy by mali nula obchodov. Pridaj --wallet {nominal * 2:.0f} "
            f"(break-even od penazenky nezavisi).")
    if settings.get("engine") != engines.FREQTRADE:
        raise SystemExit("hyperopt bezi len na engine Freqtrade (emulator MultiCharts "
                         "optimalizator nema)")

    space = ho.suggested(args.strategy) if args.suggested else {}
    for item in args.param or []:
        if "=" not in item:
            raise SystemExit(f"--param chce NAZOV=HODNOTY, dostal {item!r}")
        name, spec = item.split("=", 1)
        name = name.strip()
        if name not in params:
            raise SystemExit(f"neznámy parameter {name!r} (pozri `python -m tester.webapp.cli params`)")
        space[name] = spec.strip()
    if not space:
        raise SystemExit("hyperopt potrebuje aspoň jeden --param (alebo --suggested pre "
                         "priestor, ktorý stratégia odporúča)")
    warn_parity(space, args.strategy)

    try:
        plan = ho.build_plan(space, strategy=args.strategy, goal=args.goal, max_dd=args.max_dd,
                             min_trades=args.min_trades, note=args.note or "")
    except ValueError as exc:
        raise SystemExit(str(exc))

    znalosti = ho.knowledge_note(args.strategy)
    if znalosti:
        print(f"POZNAMKA k {args.strategy}: {znalosti}\n", file=sys.stderr)
    for varovanie in ho.warnings_for(space, args.strategy):
        print(f"POZOR: {varovanie}", file=sys.stderr)

    zadanie_txt = sweep_mod.describe(args.goal, args.max_dd, args.min_trades)
    zadanie = {"knobs": dict(space), "goal": args.goal, "max_dd": args.max_dd,
               "min_trades": args.min_trades, "epochs": int(args.epochs), "seed": args.seed,
               "verify": not args.no_verify}
    if args.jobs:
        zadanie["jobs"] = int(args.jobs)
    popis = ", ".join(f"{k}={v}" for k, v in space.items())
    note = f"hyperopt {popis}" + (f" — {args.note}" if args.note else "")
    user = args.user or getenv("USER") or ""

    print(f"hyperopt: {args.epochs} epoch, kriterium: {zadanie_txt}")
    print(f"  ladi sa: {', '.join(f'{k} = {v}' for k, v in space.items())}")
    print(f"  okno:    {settings['timerange']}  ({settings['pair']} {settings['timeframe']})",
          flush=True)

    store = RunStore()
    if args.seeds and args.seeds > 1:
        if not args.remote:
            raise SystemExit("--seeds ma zmysel na hube (--remote): seedy bezia naraz na roznych "
                             "agentoch; lokalne pusti hyperopt viackrat s --seed")
        return _hyperopt_seeds(args, params, settings, zadanie, plan, note)
    if args.remote:
        rec = _remote_execute(args, params, {**settings, "hyperopt": zadanie}, note)
        run_id = rec.get("id")
        if rec.get("status") != "done":
            raise SystemExit(f"hyperopt skoncil: {rec.get('error') or rec.get('status')}")
        det = ho.detail(rec, store.extra(run_id, "epochs.json") or [], store.all())
    elif server_alive(args.url):
        telo = {"params": params, "space": space, "goal": args.goal, "max_dd": args.max_dd,
                "min_trades": args.min_trades, "epochs": int(args.epochs), "seed": args.seed,
                "verify": not args.no_verify, "note": args.note or "", "user": user or None,
                **{k: settings.get(k) for k in ("strategy", "pair", "timeframe", "timerange",
                                                "fee", "wallet", "timeframe_detail", "engine",
                                                "exchange", "profile", "ai")}}
        if args.jobs:
            print("  (--jobs sa cez webapp neprenasa, pouzije vsetky jadra)", file=sys.stderr)
        try:
            job = api(args.url, "/api/hyperopts", telo)
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"webapp odmietla hyperopt: {exc.read().decode('utf-8', 'replace')}")
        run_id = job["id"]
        print(f"zaradene do fronty webapp: {run_id}  ({args.url})", flush=True)
        while True:
            time.sleep(5)
            det = api(args.url, f"/api/hyperopts/{run_id}")
            if det.get("status") in ("done", "failed"):
                overenia = det.get("verify") or []
                if (det["status"] == "failed" or args.no_verify or not det.get("overrides")
                        or (overenia and all(v.get("status") in ("done", "failed") for v in overenia))):
                    break
            print(f"  … {_progress_text(det.get('progress'), det.get('status'))}", flush=True)
    else:
        from ..runner import BacktestRunner

        runner = BacktestRunner(store)
        try:
            job = runner.submit(params, {**settings, "hyperopt": zadanie}, note=note, user=user)
        except (ValueError, KeyError) as exc:
            raise SystemExit(str(exc))
        run_id = job.id
        print(f"webapp nebezi, spustam priamo: {run_id}", flush=True)
        naposledy = ""
        while job.status in ("queued", "running"):
            time.sleep(3)
            # Priebeh a odhad namiesto posledneho riadku logu - Freqtrade do rury pise len
            # nove najlepsie epochy, takze log roztrhane skace a nic o case nepovie.
            text = _progress_text(getattr(job, "progress", None), job.status)
            if text != naposledy:
                print(f"  … {text}", flush=True)
                naposledy = text
        # Overovacie behy si runner zaradil sám - počká sa, kým fronta nedobehne.
        while any(j.get("status") in ("queued", "running") for j in runner.snapshot()):
            time.sleep(3)
        rec = store.get(run_id) or {}
        det = ho.detail(rec, store.extra(run_id, "epochs.json") or [],
                        store.tagged("hyperopt_run", run_id), store.log(run_id) or "")

    if det.get("status") != "done":
        raise SystemExit(f"hyperopt skoncil: {det.get('error') or det.get('status')}")
    print()
    _print_hyperopt(det, plan)
    if det.get("zero_trades"):
        # Nula obchodov vo vsetkych epochach je iny problem nez "nesplnilo mantinely" -
        # rady o --min-trades by tu posielali na nespravne miesto.
        print(f"\n{det['zero_trades']}")
        return 1
    if not det.get("overrides"):
        print("\nZIADNA epocha nesplnila mantinely (min. obchodov, strop na drawdown).")
        print("Zniz --min-trades, uvolni --max-dd, alebo daj sirsi rozsah.")
        return 1
    if args.no_verify:
        print("\nOverenie na dalsich oknach preskocene (--no-verify). Vysledok jedneho okna "
              "o strategii nepovie nic - hyperopt nasiel optimum PRAVE toho okna.")
    print(f"\ncele porovnanie: python -m tester.webapp.cli hyperopts {run_id}")
    print(f"okolie vitaza:   python -m tester.webapp.cli plateau {run_id}")
    return 0


def _hyperopt_seeds(args: argparse.Namespace, params: dict, settings: dict, zadanie: dict,
                    plan: Any, note: str) -> int:
    """Ten istý hyperopt s N seedmi naraz na hube; na konci porovnanie víťazov.

    Hyperopt sa medzi stroje deliť nedá (Optuna štúdia žije v procese Freqtradu), ale
    viac seedov paralelne povie viac než jedno dlhé hľadanie: či optimum drží, alebo je
    to tvar jedného behu.
    """
    from ... import hyperopt as ho, sweep as sweep_mod
    from ..store import RunStore

    zaklad = int(args.seed) if args.seed is not None else 1
    seeds = [zaklad + i for i in range(int(args.seeds))]
    body = [(params, {**settings, "hyperopt": {**zadanie, "seed": s}}, f"{note} [seed {s}]") for s in seeds]
    print(f"seedy {', '.join(map(str, seeds))}: {len(seeds)} hyperoptov naraz", flush=True)
    _remote_prefetch(args, body)

    store = RunStore()
    dets = []
    for i, (p_, s_, n_) in enumerate(body, 1):
        print(f"[{i}/{len(body)}] seed {seeds[i - 1]}", flush=True)
        rec = _execute(args, p_, s_, n_, quiet=True)
        if rec.get("status") != "done":
            print(f"      {rec.get('status')}: {rec.get('error') or ''}", flush=True)
            continue
        det = ho.detail(rec, store.extra(rec["id"], "epochs.json") or [], store.all())
        dets.append(det)
        over = det.get("overrides") or {}
        print(f"      {rec['id']}  vitaz: "
              + (", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in over.items()) or "ziadny")
              + (f"  — {det['verdict'].split(':')[0]}" if det.get("verdict") else ""), flush=True)

    print(f"\n=== porovnanie seedov — {sweep_mod.describe(args.goal, args.max_dd, args.min_trades)} ===")
    print(ho.compare_seeds(dets))
    if dets:
        print("\ndetail: python -m tester.webapp.cli hyperopts <id>;  okolie: cli plateau <id>")
    return 0 if dets else 1


def _print_hyperopt(det: dict, plan: Any) -> None:
    """Výpis detailu hyperoptu (`tester.hyperopt.detail`) — ten istý pre `hyperopt` aj `hyperopts`."""
    from ... import hyperopt as ho, sweep as sweep_mod

    nast, zadanie = det.get("settings") or {}, det.get("hyperopt") or {}
    print(f"=== hyperopt {det['id']} ({det.get('strategy')}) — {det.get('goal_note')} ===")
    print(f"{nast.get('pair')} {nast.get('timeframe')}, ladene okno {nast.get('timerange')}, "
          f"epoch {zadanie.get('epochs_done', '?')} z {zadanie.get('epochs', '?')}"
          + (f", profil {nast.get('profile')}" if nast.get("profile") else ""))
    print("  ladilo sa: " + ", ".join(f"{k} = {v}" for k, v in (zadanie.get("knobs") or {}).items()))
    if det.get("note"):
        print(f"  poznamka: {det['note']}")
    print()
    print(ho.table(ho.epochs_from_dicts(det.get("epochs") or []), plan))
    if det.get("overrides"):
        print("\nvitaz: " + ", ".join(f"{k}={sweep_mod._fmt(v)}" for k, v in det["overrides"].items()))
    overenia = det.get("verify") or []
    if overenia:
        print(f"\n{'okno':<22}{'stav':>8}{'obchodov':>10}{'PnL %':>9}{'break-even':>12}")
        for r in overenia:
            v = r.get("result") or {}
            znacka = "  (ladene)" if r.get("tuned") else ""
            print(f"{str(r.get('timerange') or '?'):<22}{str(r.get('status') or '?'):>8}"
                  f"{str(v.get('trades', '-')):>10}{str(v.get('pnl_pct', '-')):>9}"
                  f"{str(v.get('break_even_pct', '-')):>12}{znacka}")
        if det.get("verdict"):
            print(f"\n{det['verdict']}")
    else:
        print("\nbez overovacich behov (--no-verify, alebo este bezia)")


def cmd_hyperopts(args: argparse.Namespace) -> int:
    """Hyperopty z histórie; s argumentom detail: epochy, víťaz, overenie na oknách."""
    from ... import hyperopt as ho
    from ..store import RunStore, strategy_of

    store = RunStore()
    if args.hyperopt_id:
        rec = store.get(args.hyperopt_id)
        zadanie = ((rec or {}).get("settings") or {}).get("hyperopt") or {}
        if rec is None or not zadanie.get("knobs"):
            raise SystemExit(f"hyperopt {args.hyperopt_id} v historii nie je")
        # Bežiaca webapp vidí aj overovacie behy, ktoré ešte len bežia - detail od nej
        # je úplnejší než zo skladu.
        det = None
        if server_alive(args.url):
            try:
                det = api(args.url, f"/api/hyperopts/{args.hyperopt_id}")
            except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
                det = None
        if det is None:
            det = ho.detail(rec, store.extra(rec["id"], "epochs.json") or [],
                            store.tagged("hyperopt_run", rec["id"]), store.log(rec["id"]) or "")
        try:
            plan = ho.build_plan(zadanie["knobs"], strategy=strategy_of(rec),
                                 goal=zadanie.get("goal") or "break_even",
                                 max_dd=zadanie.get("max_dd"), min_trades=zadanie.get("min_trades"))
        except ValueError as exc:
            raise SystemExit(f"zadanie hyperoptu sa neda precitat: {exc}")
        _print_hyperopt(det, plan)
        return 0

    vsetky = [r for r in store.all() if ((r.get("settings") or {}).get("hyperopt") or {}).get("knobs")]
    if args.strategy:
        vsetky = [r for r in vsetky if strategy_of(r) == args.strategy]
    if not vsetky:
        print("v historii nie je ziadny hyperopt"
              + (f" pre strategiu {args.strategy}" if args.strategy else ""))
        return 0
    print(f"{'hyperopt':<24}{'strategia':<12}{'epoch':>7}  okno / parametre")
    for rec in sorted(vsetky, key=lambda r: r["id"], reverse=True)[:args.limit]:
        z = rec["settings"]["hyperopt"]
        print(f"{rec['id']:<24}{strategy_of(rec):<12}{str(z.get('epochs_done', '?')):>7}  "
              f"{rec['settings'].get('timerange')} | {', '.join(z['knobs'])}")
    print("\ndetail: python -m tester.webapp.cli hyperopts <hyperopt>")
    return 0
