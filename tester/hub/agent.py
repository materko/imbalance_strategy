"""Agent: hlási sa hubu, počíta, čo mu pridelí, a vyzdvihuje výsledky toho, čo sám poslal.

    agent = HubAgent(cfg, runner, store)   # runner = BacktestRunner webapp alebo vlastný
    agent.start()                          # vlákno: každých `heartbeat_seconds` jeden `tick()`

Jeden `tick()`:

1. **odovzdá** hotové výpočty — zabalí adresáre behov (u hyperoptu aj overovacie behy
   víťaza) a pošle ich hubu; kým sa upload nepodarí, skúša to pri každom ticku,
2. **heartbeat** — čo počíta, ako ďaleko to je a koľko asi ostáva (`protocol`), plus
   lokálna záťaž bez výpočtov hubu (aby ich hub nepočítal dvakrát),
3. z odpovede **vezme** pridelené výpočty do lokálneho runnera, **zruší** tie, ktoré hub
   ruší, a **vyzdvihne** výsledky výpočtov, ktoré tento agent sám zadal (zip do vlastnej
   histórie, `ack` hubu).

Čo agent počíta a čo poslal, si drží v `tester/agent_state.json` (`config.AgentState`):
po reštarte procesu bežiace behy ďalej hlási (runner ich už nemá, ale história áno) a
čakajúce výsledky si vyzdvihne.

**Verzia kódu.** Výpočet nesie commit zadávateľa (`job.version`). Agent ho pred prijatím
overí (`gitcode.has_version`); keď ho nemá, počká, kým dobehne, čo práve počíta, spraví
`git pull` (origin main) a overí znova. Keď commit nie je ani po pulle (zadávateľ ho
nepushol), výpočet zlyhá s jasnou chybou. Po pulle je kód v bežiacom procese starý:
headless agent sa reštartuje sám (`restart_on_pull`), webapp to hlási v `needs_restart`
a v `/api/hub` — Freqtrade beží v podprocese, takže samotný beh už ide na novom kóde.
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import gitcode
from . import protocol as P
from .client import HubError, HubHttp
from .config import AgentConfig, AgentState, load_state, save_state
from .transfer import pack_runs, unpack_runs

__all__ = ["HubAgent"]

log = logging.getLogger(__name__)

#: Hotový **hyperopt** sa odovzdá až po toľkých tickoch v konečnom stave — overovacie behy
#: víťaza si zaraďuje tesne po tom, čo nastaví `done`, a jeden tick medzi tým to bezpečne
#: preklenie. Backtest nič nezaraďuje, ten ide hneď.
SETTLE_TICKS = 2


def _parse_iso(text: str | None) -> float | None:
    if not text:
        return None
    try:
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


class HubAgent:
    def __init__(self, cfg: AgentConfig, runner: Any, store: Any, *, http: HubHttp | None = None,
                 state_path: Path | None = None, clock: Callable[[], float] = time.time,
                 version: str = "") -> None:
        self.cfg = cfg
        self.runner = runner
        self.store = store
        self.http = http or HubHttp(cfg.hub_url, cfg.token)
        self.state_path = state_path
        self.clock = clock
        self.version = version or gitcode.version()
        #: Headless agent sa po pulle reštartuje (nový proces = nový kód); webapp nie.
        self.restart_on_pull = False
        self.needs_restart = False
        #: Po pulle: kód na disku je novší než ten v tomto procese.
        self.code_changed = False
        self.instance = uuid.uuid4().hex[:12]
        self.cores = os.cpu_count() or 1
        self.slots = cfg.slots(self.cores)
        self.state: AgentState = load_state(state_path)
        self.registered = False
        self.last_error: str | None = None
        self.last_ok: float | None = None
        self.ticks = 0
        #: Koľko tickov je lokálny beh výpočtu už v konečnom stave (odovzdá sa po SETTLE_TICKS).
        self._final_ticks: dict[str, int] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- vlákno ------------------------------------------------------------- #

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="hub-agent", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as exc:  # noqa: BLE001 - výpadok hubu nesmie zhodiť agenta
                self.registered = False
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("hub agent: %s", self.last_error)
            self._stop.wait(self.cfg.heartbeat_seconds)

    # -- jeden krok --------------------------------------------------------- #

    def tick(self) -> dict[str, Any]:
        self.ticks += 1
        if not self.registered:
            self._register()
        self.version = gitcode.version() or self.version
        self._upload_finished()
        odpoved = self.http.post(f"/api/agents/{self.cfg.name}/heartbeat", self._heartbeat_body())
        for job in odpoved.get("assign") or []:
            self._accept(job)
        for job_id in odpoved.get("cancel") or []:
            self._cancel(job_id)
        for job in odpoved.get("finished") or []:
            self._collect(job)
        self.last_ok = self.clock()
        self.last_error = None
        return odpoved

    def _register(self) -> None:
        self.http.post("/api/agents/register", {
            "name": self.cfg.name, "instance": self.instance, "cores": self.cores,
            "slots": self.slots, "accept": self.cfg.accept, "send": self.cfg.send,
            "version": self.version,
        })
        self.registered = True

    def bye(self) -> None:
        """Odhlásenie pred reštartom: hub meno uvoľní hneď a pridelené výpočty podrží."""
        try:
            self.http.post(f"/api/agents/{self.cfg.name}/bye")
        except (HubError, OSError, ValueError):
            pass
        self.registered = False

    # -- heartbeat ---------------------------------------------------------- #

    def _hub_run_ids(self) -> set[str]:
        return {e.get("run_id") for e in self.state.computing.values() if e.get("run_id")}

    def _local_load(self) -> dict[str, Any]:
        """Lokálna fronta bez výpočtov hubu: čo si tester spustil sám."""
        nase = self._hub_run_ids()
        bezia: list[dict[str, Any]] = []
        caka = 0
        for j in self.runner.snapshot():
            if j.get("id") in nase:
                continue
            if j.get("status") == "running":
                bezia.append(j)
            elif j.get("status") == "queued":
                caka += 1
        eta = 0.0
        historia = None
        for j in bezia:
            s = j.get("settings") or {}
            if historia is None:
                historia = self.store.all()
            odhad = P.estimate_seconds(s, historia, cores=self.cores)
            uplynulo = max(0.0, self.clock() - (_parse_iso(j.get("started")) or self.clock()))
            eta = max(eta, P.remaining_seconds(odhad, uplynulo, None))
        return {"running": len(bezia), "queued": caka,
                "exclusive": any(P.kind_of(j.get("settings") or {}) == P.KIND_HYPEROPT for j in bezia),
                "eta_seconds": eta if bezia else None}

    def _report(self, job_id: str, entry: dict[str, Any]) -> dict[str, Any] | None:
        """Stav jedného výpočtu hubu pre heartbeat; `None`, keď beh lokálne neexistuje."""
        run_id = entry.get("run_id")
        if not run_id:
            return None
        job = self.runner.job(run_id)
        if job is not None:
            status = job.status
            settings, log_lines, started = job.settings, job.log_lines, job.started
        else:
            rec = self.store.get(run_id)
            if rec is None:
                return None
            status = rec.get("status") or "failed"
            settings, log_lines, started = rec.get("settings") or {}, [], rec.get("started")
        if status in ("done", "failed"):
            overenia = self._live_verifications(run_id)
            if not overenia:
                return {"id": job_id, "status": status, "run_id": run_id, "progress": 1.0,
                        "eta_seconds": 0.0}
            # Hyperopt dobehol, ale víťaz ešte beží na referenčných oknách — výpočet nie je
            # hotový a stroj nie je voľný. Zvyšok je najdlhšie z toho, čo ešte beží alebo čaká.
            hotove = len(self._verification_ids(run_id))
            eta = 0.0
            historia = self.store.all()
            for j in overenia:
                odhad = P.estimate_seconds(j.get("settings") or {}, historia, cores=self.cores)
                zacal = _parse_iso(j.get("started")) if j.get("status") == "running" else None
                uplynulo = max(0.0, self.clock() - zacal) if zacal else 0.0
                eta = max(eta, P.remaining_seconds(odhad, uplynulo, None))
            podiel = hotove / float(hotove + len(overenia))
            return {"id": job_id, "status": "running", "run_id": run_id,
                    "progress": round(0.8 + 0.2 * podiel, 3), "eta_seconds": round(eta, 1),
                    "elapsed_seconds": round(max(0.0, self.clock() - (_parse_iso(started) or self.clock())), 1)}
        uplynulo = max(0.0, self.clock() - (_parse_iso(started) or self.clock())) if started else 0.0
        odhad = entry.get("estimate_seconds")
        if odhad is None:
            odhad = P.estimate_seconds(settings, self.store.all(), cores=self.cores)
            entry["estimate_seconds"] = odhad
        epochs = (settings.get("hyperopt") or {}).get("epochs") if P.kind_of(settings) == P.KIND_HYPEROPT else None
        postup = P.progress_from_log(log_lines, epochs) if epochs else None
        if epochs and postup is None and started:
            # Freqtrade bez terminálu priebeh nevypisuje; epochy ale priebežne zapisuje
            # do `.fthypt`, ktorý vznikol po štarte behu.
            from ..hyperopt import latest_results

            postup = P.progress_from_results(latest_results(_parse_iso(started) or 0.0), epochs)
        zvysok = P.remaining_seconds(float(odhad), uplynulo, postup) if status == "running" else float(odhad)
        return {"id": job_id, "status": "running", "run_id": run_id, "progress": postup,
                "eta_seconds": round(zvysok, 1), "elapsed_seconds": round(uplynulo, 1)}

    def _heartbeat_body(self) -> dict[str, Any]:
        jobs = []
        for job_id, entry in list(self.state.computing.items()):
            r = self._report(job_id, entry)
            if r is not None:
                jobs.append(r)
        return {"instance": self.instance, "accept": self.cfg.accept, "send": self.cfg.send,
                "cores": self.cores, "slots": self.slots, "version": self.version,
                "needs_restart": self.needs_restart, "load": self._local_load(), "jobs": jobs}

    # -- výpočty od hubu ---------------------------------------------------- #

    def _fail(self, job_id: str, error: str) -> None:
        self.http.post_bytes(f"/api/jobs/{job_id}/result?status=failed&agent={self.cfg.name}"
                             f"&version={_q(self.version)}&error={_q(error[:500])}", b"")

    def _ensure_version(self, job: dict[str, Any]) -> bool:
        """Má tento klon commit zadávateľa? Keď nie, pull — ale až keď nič nepočíta.

        Vráti True, keď sa výpočet smie prijať teraz. False = počkať (hub ho pošle znova
        v ďalšom heartbeate), alebo už zlyhal.
        """
        wanted = job.get("version")
        if gitcode.has_version(wanted):
            return True
        if self.state.computing:
            log.info("hub agent: výpočet %s chce commit %s, čakám na dobehnutie %d behov",
                     job["id"], wanted, len(self.state.computing))
            return False
        if self.needs_restart:
            return False  # pull už bol, čaká sa na reštart
        r = gitcode.pull()
        self.version = gitcode.version() or self.version
        if not gitcode.has_version(wanted):
            vystup = (r.get("output") or "").strip()[-300:]
            self._fail(job["id"], f"agent {self.cfg.name} nemá commit {wanted} ani po git pull "
                                  f"(HEAD {self.version}) — zadávateľ ho musí pushnúť do main. {vystup}")
            return False
        self.code_changed = True
        self._sync_data()
        if self.restart_on_pull:
            self.needs_restart = True  # nový proces si výpočet vezme s novým kódom
            return False
        log.warning("hub agent: po git pull beží tento proces na starom kóde — reštartuj webapp")
        return True

    def _sync_data(self) -> None:
        """Po pulle: čo pribudlo v `data_archive/`, zložiť do skladu, a dopočítať timeframy.

        Rovnaký commit = rovnaké dáta pre všetkých agentov — ale len keď si ich agent po
        pulle aj rozbalí; inak by beh na novom páre spadol až vo Freqtrade.
        """
        from .. import data_archive, timeframes

        try:
            if data_archive.missing():
                log.info("hub agent: skladam nove data z archivu")
                data_archive.main(["merge"])
            if timeframes.missing():
                timeframes.ensure()
        except Exception as exc:  # noqa: BLE001 - nech to povie beh, nie agent
            log.warning("hub agent: data po pulle sa nepodarilo zlozit: %s", exc)

    def _accept(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        if job_id in self.state.computing:
            return  # hub ho posiela, kým ho nenahlásime ako bežiaci — už ho máme
        if not self._ensure_version(job):
            return
        payload = job.get("payload") or {}
        # Beh v histórii agenta (a po vrátení aj zadávateľa) nesie, odkiaľ prišiel a na
        # akom kóde bežal — inak by sa o týždeň nedalo povedať, prečo dal iné čísla.
        settings = {**(payload.get("settings") or {}),
                    "hub": {"job": job_id, "submitter": job.get("submitter"),
                            "version_requested": job.get("version"), "version": self.version,
                            "agent": self.cfg.name}}
        try:
            local = self.runner.submit(payload["params"], settings,
                                       note=payload.get("note") or "", user=payload.get("user") or "")
        except Exception as exc:  # noqa: BLE001 - zlý config nech zlyhá ako výpočet, nie ako agent
            self._fail(job_id, str(exc))
            return
        self.state.computing[job_id] = {"run_id": local.id, "kind": job.get("kind"),
                                        "accepted": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        save_state(self.state, self.state_path)

    def _cancel(self, job_id: str) -> None:
        entry = self.state.computing.get(job_id)
        if entry is None:
            # nič také nepočítame — hubu to povieme hneď, nech nečaká
            self.http.post_bytes(f"/api/jobs/{job_id}/result?status=cancelled&agent={self.cfg.name}", b"")
            return
        entry["cancel_requested"] = True
        save_state(self.state, self.state_path)
        run_id = entry.get("run_id")
        if run_id:
            self.runner.cancel(run_id)
            # aj overovacie behy víťaza, keby už boli vo fronte
            for j in self.runner.snapshot():
                if ((j.get("settings") or {}).get("hyperopt_run") or {}).get("id") == run_id:
                    self.runner.cancel(j["id"])

    def _live_verifications(self, run_id: str) -> list[dict[str, Any]]:
        """Overovacie behy víťaza, ktoré ešte bežia alebo čakajú v lokálnom runneri."""
        return [j for j in self.runner.snapshot()
                if ((j.get("settings") or {}).get("hyperopt_run") or {}).get("id") == run_id]

    def _verification_ids(self, run_id: str) -> list[str]:
        return [r["id"] for r in self.store.all()
                if (((r.get("settings") or {}).get("hyperopt_run") or {}).get("id")) == run_id]

    def _settled(self, run_id: str) -> tuple[bool, str]:
        """(je hotové, stav) — hotové = lokálny beh v konečnom stave a nič, čo naň nadväzuje, nežije."""
        job = self.runner.job(run_id)
        if job is not None:
            status = job.status
        else:
            rec = self.store.get(run_id)
            status = (rec or {}).get("status") or "failed"
        if status not in ("done", "failed"):
            return False, status
        if self._live_verifications(run_id):
            return False, status
        return True, status

    def _upload_finished(self) -> None:
        for job_id, entry in list(self.state.computing.items()):
            run_id = entry.get("run_id")
            if not run_id:
                continue
            hotove, status = self._settled(run_id)
            if not hotove:
                self._final_ticks.pop(job_id, None)
                continue
            n = self._final_ticks.get(job_id, 0) + 1
            self._final_ticks[job_id] = n
            if entry.get("kind") == P.KIND_HYPEROPT and n < SETTLE_TICKS:
                continue
            run_ids = [run_id] + self._verification_ids(run_id)
            data = pack_runs(self.store.root, run_ids)
            if entry.get("cancel_requested") and status != "done":
                stav, chyba = "cancelled", ""  # kto a prečo dopíše hub (`cancelled_by`)
            else:
                stav = status
                chyba = ((self.store.get(run_id) or {}).get("error") or "") if status == "failed" else ""
            q = (f"?status={stav}&agent={self.cfg.name}&version={_q(self.version)}"
                 f"&run_ids={','.join(run_ids)}")
            if chyba:
                q += f"&error={_q(chyba[:500])}"
            try:
                self.http.post_bytes(f"/api/jobs/{job_id}/result{q}", data)
            except HubError as exc:
                if exc.status != 404:
                    raise
            self.state.computing.pop(job_id, None)
            self._final_ticks.pop(job_id, None)
            save_state(self.state, self.state_path)

    # -- výsledky toho, čo sme poslali -------------------------------------- #

    def note_sent(self, job: dict[str, Any], note: str = "") -> None:
        """Zapíše, že sme výpočet zadali — heartbeat si potom výsledok vyzdvihne sám."""
        self.state.sent[job["id"]] = {
            "kind": job.get("kind"), "note": note, "created": job.get("created"),
            "status": job.get("status"), "run_ids": [], "error": None,
        }
        save_state(self.state, self.state_path)

    def _collect(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        zaznam = self.state.sent.setdefault(job_id, {"kind": job.get("kind"), "note": job.get("note") or "",
                                                     "created": job.get("created"), "run_ids": []})
        run_ids: list[str] = []
        if job.get("has_result"):
            try:
                data = self.http.get_bytes(f"/api/jobs/{job_id}/result")
            except HubError as exc:
                if exc.status != 410:
                    raise
                data = b""
            if data:
                run_ids = unpack_runs(data, self.store.root)
        zaznam.update({"status": job.get("status"), "error": job.get("error"),
                       "run_ids": run_ids or list(job.get("run_ids") or []),
                       "agent": job.get("agent"),
                       "collected": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        save_state(self.state, self.state_path)
        self.http.post(f"/api/jobs/{job_id}/ack")

    # -- stav pre API ------------------------------------------------------- #

    def public(self) -> dict[str, Any]:
        return {
            "name": self.cfg.name, "hub_url": self.cfg.hub_url, "accept": self.cfg.accept,
            "send": self.cfg.send, "cores": self.cores, "slots": self.slots,
            "version": self.version, "needs_restart": self.needs_restart,
            "code_changed": self.code_changed,
            "registered": self.registered, "last_error": self.last_error,
            "last_ok": datetime.fromtimestamp(self.last_ok, tz=timezone.utc).isoformat(timespec="seconds")
            if self.last_ok else None,
            "computing": {k: dict(v) for k, v in self.state.computing.items()},
            "sent": {k: dict(v) for k, v in self.state.sent.items()},
        }


def _q(text: str) -> str:
    from urllib.parse import quote
    return quote(text, safe="")
