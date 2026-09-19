"""Fronta a spúšťanie Freqtrade backtestu v podprocese.

Predvolene jeden beh naraz: Freqtrade s `--timeframe-detail 1m` vyťaží jedno jadro a na
notebooku testera by si dva behy len prekážali. Server s viac jadrami (agent v
`tester.hub`) si zapne `workers=N` — každý beh dostane vlastný adresár výsledkov
(`backtest_results/<run_id>/`), takže sa zipy nepomiešajú. Hyperopt je **exkluzívny**:
vyťaží všetky jadrá, preto sa nespustí, kým beží čokoľvek iné, a kým beží on, nezačne
nič ďalšie (`Job.exclusive`).

Parametre stratégie idú do Freqtradu cez dočasný JSON profil a premennú
`TRADEBOT_PROFILE` — presne tak, ako to robí stratégia pri ručnom spúšťaní. Nastavenia
behu (pár, obdobie, poplatok, peňaženka, 1m detail) idú cez CLI prepínače.

Cez `TRADEBOT_DRAW_OUT` si beh vypýta od stratégie aj kresby enginu (zóny, TP/SL boxy,
štítky…) — po dobehnutí idú do lokálnej cache grafov (`runs/.charts/`, nie do gitu) a detail
behu z nich kreslí graf páru. Keď cache nie je (beh z gitu od iného testera), graf sa
prepočíta z uloženého configu (`tester.webapp.replay`).

Bod mriežky, bunka matice, overenie víťaza hyperoptu a sused víťaza (`batches.KINDS`)
do histórie nejdú: uloží sa len riadok výsledku do `sweeps/` a kresby sa ani nežiadajú.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import REPO, BACKTEST_RESULTS as RESULTS_DIR, TMP_PROFILES
from tradebot.core.types import INSTRUMENTS

from .. import engines
from .batches import batch_tag
from .command import build_command, effective_params, kill_tree, write_profile
from .hyperopt_job import HyperoptJobMixin
from .market import check_market_rules, instrument_for_pair
from .results import result_from_zip, run_multicharts, zero_trade_warning
from .store import RunStore, make_run_id

# Verejné mená z čias, keď bolo všetko v tomto module — importujú ich testy aj tester.*.
from .market import (  # noqa: F401
    BINANCE_FUTURES, BINANCE_SPOT, available_pairs, only_1m_on_disk, is_multicharts_pair,
)
from .command import tf_minutes  # noqa: F401
from .results import entry_signals, timerange_ms  # noqa: F401
from .repo_profiles import (  # noqa: F401
    default_params, list_profiles, profile_instruments, profile_titles, profile_info,
)


#: Koľko riadkov logu sa uloží k behu — celý log Freqtradu má stovky riadkov
#: o načítavaní dát, ktoré nikoho nezaujímajú.
LOG_KEEP_LINES = 400


@dataclass
class Job:
    id: str
    params: dict[str, Any]
    settings: dict[str, Any]
    note: str = ""
    user: str = ""
    status: str = "queued"  # queued | running | done | failed
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    started: str | None = None
    finished: str | None = None
    error: str | None = None
    log_lines: list[str] = field(default_factory=list)
    proc: subprocess.Popen | None = None
    cancel_requested: bool = False

    @property
    def exclusive(self) -> bool:
        """Hyperopt vyťaží všetky jadrá — vedľa neho nemá bežať nič (`BacktestRunner.workers`)."""
        return bool((self.settings.get("hyperopt") or {}).get("knobs"))

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "status": self.status, "created": self.created, "started": self.started,
            "finished": self.finished, "error": self.error, "settings": self.settings,
            "note": self.note, "user": self.user, "log_tail": self.log_lines[-40:],
            "progress": getattr(self, "progress", None),
        }


class BacktestRunner(HyperoptJobMixin):
    """Fronta jedného pracovného vlákna. `submit()` vráti Job, výsledok skončí v store."""

    def __init__(self, store: RunStore, python: str | None = None,
                 command_builder: Callable[[str, Path, dict[str, Any]], list[str]] = build_command,
                 workers: int = 1) -> None:
        self.store = store
        self.python = python or sys.executable
        self.build_command = command_builder
        #: Koľko behov naraz. 1 = správanie pre notebook testera; agent hubu si dá
        #: toľko, koľko má jadier na rozdanie (`tester.hub.agent`).
        self.workers = max(1, int(workers))
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self._q: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        #: Stráži exkluzivitu: hyperopt čaká, kým dobehne všetko ostatné, a ostatné
        #: čakajú, kým dobehne hyperopt. Worker s takým behom v ruke tu stojí.
        self._slot = threading.Condition(self._lock)
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        zive = [t for t in self._threads if t.is_alive()]
        for i in range(len(zive), self.workers):
            t = threading.Thread(target=self._loop, name=f"ibs-backtest-worker-{i}", daemon=True)
            t.start()
            zive.append(t)
        self._threads = zive

    # -- vyťaženie (pre agenta hubu) ---------------------------------------- #

    def load(self) -> dict[str, Any]:
        """Čo práve beží: počet behov, či medzi nimi je exkluzívny, koľko čaká."""
        with self._lock:
            bezia = [self.jobs[i] for i in self.order if self.jobs[i].status == "running"]
            caka = sum(1 for i in self.order if self.jobs[i].status == "queued")
        return {"running": len(bezia), "exclusive": any(j.exclusive for j in bezia),
                "queued": caka, "workers": self.workers}

    def submit(self, params: dict[str, Any], settings: dict[str, Any], note: str = "", user: str = "") -> Job:
        # config sa validuje HNEĎ, aby tester dostal chybu do formulára a nie do logu behu,
        # a beh si zapíše celý efektívny config — nie len to, čo poslal formulár
        params = effective_params(params, settings.get("strategy") or "ibs")
        check_market_rules(settings["pair"], params)
        settings = {**settings, "instrument": instrument_for_pair(settings["pair"])}
        job = Job(id=make_run_id(params, settings), params=params, settings=settings, note=note, user=user)
        with self._lock:
            self.jobs[job.id] = job
            self.order.append(job.id)
        self._q.put(job.id)
        self.start()
        return job

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job is None:
            return False
        job.cancel_requested = True
        if job.status == "queued":
            job.status = "failed"
            job.error = "zrušené používateľom"
            job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
            self._persist(job, None)
            return True
        if job.proc is not None and job.proc.poll() is None:
            kill_tree(job.proc.pid)
            return True
        return False

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.jobs[i].public() for i in self.order if self.jobs[i].status in ("queued", "running")]

    def job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    # -- vnútro ------------------------------------------------------------ #

    def _can_start(self, job: Job) -> bool:
        """Volať so zamknutým `_lock`: exkluzívny beh chce prázdny stroj, ostatné len
        stroj bez exkluzívneho behu."""
        bezia = [self.jobs[i] for i in self.order if self.jobs[i].status == "running"]
        if job.exclusive:
            return not bezia
        return not any(j.exclusive for j in bezia)

    def _loop(self) -> None:
        while True:
            job_id = self._q.get()
            job = self.jobs.get(job_id)
            if job is None or job.status != "queued":
                continue
            with self._slot:
                while not self._can_start(job) and not job.cancel_requested:
                    self._slot.wait(timeout=1.0)
                if job.status != "queued":  # zrušené počas čakania na slot
                    continue
                job.status = "running"
            try:
                self._run(job)
            except Exception:  # noqa: BLE001 - chyba behu nesmie zabiť worker
                job.status = "failed"
                job.error = traceback.format_exc()[-2000:]
                job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self._persist(job, None)
            finally:
                with self._slot:
                    self._slot.notify_all()

    def _run(self, job: Job) -> None:
        job.status = "running"
        job.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        t0 = time.time()
        instrument = instrument_for_pair(job.settings["pair"])
        profile = write_profile(job.id, job.params, instrument, job.settings.get("strategy") or "ibs")
        # Engine si volí tester; keď nepovie, rozhodne to, čo je na disku (tester.engines).
        # Hyperopt je iny druh behu: vysledkom nie su obchody, ale epochy - a po nich
        # overovacie behy na referencnych oknach. Ide tou istou frontou, lebo vytazi
        # vsetky jadra a beh vedla neho by mal cudzie casy.
        if (job.settings.get("hyperopt") or {}).get("knobs"):
            self._run_hyperopt(job, instrument, profile, t0)
            return
        engine = job.settings.get("engine") or engines.default_engine(
            INSTRUMENTS[instrument], job.settings.get("timeframe") or "3m")
        if engine == engines.MULTICHARTS:
            self._run_multicharts(job, instrument, profile, t0)
            return
        cmd = self.build_command(self.python, profile, job.settings)
        # Vlastný adresár výsledkov: pri viacerých workeroch by sa inak nedalo povedať,
        # ktorý zip v `backtest_results/` patrí ktorému behu.
        results_dir = RESULTS_DIR / job.id
        results_dir.mkdir(parents=True, exist_ok=True)
        if cmd and cmd[0] == self.python:
            cmd = cmd + ["--backtest-directory", str(results_dir)]
        job.log_lines.append("$ " + " ".join(cmd))

        chart_tmp = TMP_PROFILES / f"{job.id}.chart.json.gz"
        env = dict(os.environ, TRADEBOT_PROFILE=str(profile),
                   PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        env.pop("TRADEBOT_DRAW_OUT", None)
        # Bod mriežky kresby nepotrebuje — do histórie nejde a export stojí čas aj disk.
        if batch_tag(job.settings) is None:
            env["TRADEBOT_DRAW_OUT"] = str(chart_tmp)
        before = {p.name for p in results_dir.glob("*.zip")}

        job.proc = subprocess.Popen(
            cmd, cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        assert job.proc.stdout is not None
        for line in job.proc.stdout:
            job.log_lines.append(line.rstrip("\n"))
            if len(job.log_lines) > 5000:
                del job.log_lines[:1000]
        rc = job.proc.wait()
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        duration = round(time.time() - t0, 1)
        # Beh bez zipu (chyba, zrušenie, falošný príkaz v testoch) nech nenechá prázdny adresár.
        if not any(results_dir.iterdir()):
            results_dir.rmdir()

        if job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            chart_tmp.unlink(missing_ok=True)
            return
        if rc != 0:
            job.status = "failed"
            job.error = f"freqtrade skončil s kódom {rc}"
            self._persist(job, None, duration)
            chart_tmp.unlink(missing_ok=True)
            return

        new = sorted(
            (p for p in results_dir.glob("*.zip") if p.name not in before),
            key=lambda p: p.stat().st_mtime,
        )
        if not new:
            job.status = "failed"
            job.error = "freqtrade skončil, ale nevytvoril výsledkový zip"
            self._persist(job, None, duration)
            return

        summary, trades, series = result_from_zip(new[-1])
        summary["duration_s"] = duration
        summary["zip"] = new[-1].name
        warning = zero_trade_warning(summary, job.log_lines)
        if warning:
            summary["warning"] = warning
            job.log_lines.append("POZOR: " + warning)
        job.status = "done"
        self._persist(job, (summary, trades, series), duration, chart_path=chart_tmp)

    def _run_multicharts(self, job: Job, instrument: str, profile: Path, t0: float) -> None:
        """Beh na „burze" MultiCharts: emulátor MultiCharts v tomto procese, bez Freqtrade.

        Ten istý `MCRunner` ako študia v MultiCharts, 1m sviečky z `data/multicharts/`,
        výsledok v tvare Freqtrade behu — história webapp ich nerozlišuje.
        """
        chart_tmp = TMP_PROFILES / f"{job.id}.chart.json.gz"
        out = run_multicharts(
            job.params, job.settings, profile,
            log=lambda s: job.log_lines.append(s), should_stop=lambda: job.cancel_requested,
            chart_out=chart_tmp if batch_tag(job.settings) is None else None)
        duration = round(time.time() - t0, 1)
        job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if out is None or job.cancel_requested:
            job.status = "failed"
            job.error = "zrušené používateľom"
            self._persist(job, None, duration)
            chart_tmp.unlink(missing_ok=True)
            return
        summary, rows, series, _ = out
        summary["duration_s"] = duration
        job.status = "done"
        self._persist(job, (summary, rows, series), duration, chart_path=chart_tmp)

    def _persist(self, job: Job, result, duration: float | None = None,
                 chart_path: Path | None = None) -> None:
        record = {
            "id": job.id,
            "status": job.status,
            "created": job.created,
            "started": job.started,
            "finished": job.finished,
            "user": job.user,
            "note": job.note,
            "settings": job.settings,
            "params": job.params,
            "error": job.error,
            "result": None,
            "series": None,
        }
        trades = None
        if result is not None:
            summary, trades, series = result
            record["result"] = summary
            record["series"] = series
        elif duration is not None:
            record["result"] = {"duration_s": duration}
        tag = batch_tag(job.settings)
        if tag is not None:
            # Bod celku: len riadok výsledku do `sweeps/`, do histórie nič.
            if chart_path is not None:
                Path(chart_path).unlink(missing_ok=True)
            record.pop("series", None)
            extra = {}
            if tag[0] == "hyperopt_run" and trades:
                from .. import plateau as pl

                # Test okolia víťaza meria susedov intervalom víťaza z Monte Carla — a na to
                # treba obchody, ktoré bod neukladá. Interval sa preto spočíta teraz.
                lo, hi = pl.winner_ci(record, trades)
                if lo is not None:
                    extra["break_even_ci"] = {"lo": lo, "hi": hi, "trades": len(trades),
                                              "iterations": pl.MC_ITERATIONS, "seed": pl.MC_SEED}
            if job.status == "failed" and job.log_lines:
                # Log bodu sa neukladá; pri chybe aspoň jeho koniec, inak nie je z čoho zistiť prečo.
                extra["log_tail"] = [line[-300:] for line in job.log_lines[-15:]]
            self.store.batches.add_point(record, extra)
            return
        log = "\n".join(_trim_log(job.log_lines))
        self.store.save(record, trades, log, chart_path=chart_path)


def _trim_log(lines: list[str]) -> list[str]:
    """Nechá hlavičku, varovania a záver — načítavanie dát nikoho nezaujíma."""
    if len(lines) <= LOG_KEEP_LINES:
        return lines
    keep_head = lines[:5]
    interesting = [l for l in lines[5:] if any(k in l for k in ("WARNING", "ERROR", "IBS", "Traceback"))]
    tail = lines[-(LOG_KEEP_LINES - len(keep_head) - len(interesting)):] if LOG_KEEP_LINES > len(keep_head) + len(interesting) else lines[-100:]
    return keep_head + ["… (skrátené) …"] + interesting + ["…"] + tail
