"""Graf behu na vyžiadanie — kresby enginu prepočítané z uloženého configu.

    python -m tester.webapp.replay 20260917-113949-8a85ce      # to isté, čo robí webapp

### Prečo
Kresby (zóny, TP/SL boxy, štítky) majú megabajt na beh a do gitu nejdú. Beh ale nesie
celý efektívny config — stratégiu, parametre, pár, TF, okno, poplatok, peňaženku, engine —
takže kresby sa dajú vyrobiť znova, keď graf niekto otvorí. Výsledok ostane v lokálnej
cache (`runs/.charts/`), druhé otvorenie je okamžité.

### Najlacnejší správny prepočet
* **Emulátor MultiCharts**: kresby aj obchody vznikajú v jednom prechode, takže sa beh
  prehrá celý (`runner.run_multicharts`, ten istý kód ako backtest) a obchody sa porovnajú
  s `trades.json` kus po kuse.
* **Freqtrade**: kresby kreslí engine v `populate_indicators` nad sviečkami TF grafu a fill
  model Freqtradu (1m detail, simulácia obchodov) do nich nezasahuje. Stačí preto urobiť
  presne to, čo backtest robí pred simuláciou — načítať dáta tým istým `Backtesting`
  (rovnaké okno aj predhistória) a zavolať `advise_all_indicators`. Bez 1m detailu a bez
  simulácie je to asi o tretinu lacnejšie a do `backtest_results/` sa nič nezapíše, takže
  sa to nebije s frontou backtestov. Kontrola ide po signáloch: každý obchod v `trades.json`
  nesie v `enter_tag` čas baru signálu a prepočítaný engine tam musí mať signál toho istého
  smeru.

Keď kontrola nesedí (starý beh bez úplného configu, zmenený kód stratégie, iné dáta), graf
sa aj tak ukáže — s viditeľným varovaním, že kresby nemusia patriť k obchodom behu.

### Beh na pozadí
`ChartReplayer` má vlastné pracovné vlákno a každý prepočet púšťa ako podproces (Freqtrade
si nastavuje globálny logging a burzu, emulátor drží GIL) — HTTP dopyt len zaradí prácu
a stránka sa pýta na stav. S frontou backtestov nezdieľa nič: ani vlákno, ani adresár
výsledkov, ani dočasné profily.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tradebot.core.paths import REPO

__all__ = ["compute", "ChartReplayer", "compare_trades", "check_signals", "main"]

#: Koľko rozdielnych obchodov sa vypíše do varovania — viac nikto čítať nebude.
SAMPLE = 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# kontrola: patria prepočítané kresby k obchodom behu?
# --------------------------------------------------------------------------- #


def _trade_key(t: dict[str, Any]) -> tuple:
    def r(v: Any) -> float | None:
        return None if v is None else round(float(v), 6)

    return (str(t.get("open_date"))[:19], str(t.get("close_date"))[:19], bool(t.get("is_short")),
            r(t.get("open_rate")), r(t.get("close_rate")))


def compare_trades(stored: list[dict[str, Any]], replayed: list[dict[str, Any]]) -> dict[str, Any]:
    """Obchody behu proti prepočítaným: vstup, výstup, smer a ceny musia sedieť."""
    a = [_trade_key(t) for t in stored]
    b = [_trade_key(t) for t in replayed]
    zvysok = list(b)
    chyba_v_prepocte = []
    for k in a:
        if k in zvysok:
            zvysok.remove(k)
        else:
            chyba_v_prepocte.append(k)
    return {
        "stored_trades": len(a), "replayed_trades": len(b),
        "matched": len(a) - len(chyba_v_prepocte),
        "only_stored": [list(k) for k in chyba_v_prepocte[:SAMPLE]],
        "only_replayed": [list(k) for k in zvysok[:SAMPLE]],
        "match": not chyba_v_prepocte and not zvysok,
    }


def check_signals(stored: list[dict[str, Any]], rows: dict[int, Any], prefix: str) -> dict[str, Any]:
    """Freqtrade: za každým obchodom musí byť v prepočte signál toho istého smeru."""
    ok, chyba, bez_tagu = 0, [], 0
    for t in stored:
        tag = str(t.get("enter_tag") or "")
        if not tag.startswith(prefix):
            bez_tagu += 1
            continue
        try:
            ts = int(tag[len(prefix):])
        except ValueError:
            bez_tagu += 1
            continue
        row = rows.get(ts)
        smer = (getattr(row, "enter_short", 0) if t.get("is_short") else getattr(row, "enter_long", 0)) if row else 0
        if smer:
            ok += 1
        else:
            chyba.append(str(t.get("open_date"))[:19])
    return {"stored_trades": len(stored), "signals_ok": ok, "signals_missing": len(chyba),
            "missing": chyba[:SAMPLE], "untagged": bez_tagu,
            "match": not chyba and ok == len(stored)}


def _incomplete(rec: dict[str, Any]) -> list[str]:
    """Prečo config behu nemusí byť úplný — beh spred zápisu celého efektívneho configu."""
    from tradebot.strategies import get_spec

    from .store import strategy_of

    out = []
    nast = rec.get("settings") or {}
    if not nast.get("instrument"):
        out.append("beh nemá zapísaný inštrument (starší záznam)")
    try:
        chyba = sorted(set(get_spec(strategy_of(rec)).config_cls().to_dict()) - set(rec.get("params") or {}))
    except KeyError:
        chyba = []
    if chyba:
        out.append(f"{len(chyba)} parametrov chýba a doplnia sa dnešnými defaultmi "
                   f"({', '.join(chyba[:4])}{'…' if len(chyba) > 4 else ''})")
    if not nast.get("engine"):
        out.append("engine nie je zapísaný, berie sa Freqtrade")
    return out


def _warning(check: dict[str, Any]) -> str | None:
    if check.get("match"):
        return None
    if "replayed_trades" in check:
        text = (f"Prepočítaný graf nesedí s obchodmi behu: v behu {check['stored_trades']}, "
                f"v prepočte {check['replayed_trades']}, zhodných {check['matched']}.")
    else:
        text = (f"Prepočítaný graf nesedí s obchodmi behu: signál engine chýba pri "
                f"{check.get('signals_missing', 0)} z {check.get('stored_trades', 0)} obchodov"
                + (f", {check['untagged']} obchodov sa overiť nedá (bez času signálu)"
                   if check.get("untagged") else "") + ".")
    if check.get("incomplete"):
        text += " Pravdepodobná príčina: " + "; ".join(check["incomplete"]) + "."
    else:
        text += " Zmenil sa kód stratégie alebo dáta od času behu."
    return text + " Kresby nemusia patriť k obchodom v tabuľke."


# --------------------------------------------------------------------------- #
# prepočet
# --------------------------------------------------------------------------- #


def _freqtrade_rows(rec: dict[str, Any], profile: Path, out: Path, log: Callable[[str], None],
                    python: str) -> tuple[dict[int, Any], str]:
    """Kresby Freqtrade behu: dáta a indikátory presne ako backtest, bez simulácie obchodov."""
    from tester.ftexchange import register
    from freqtrade.commands import Arguments
    from freqtrade.commands.optimize_commands import setup_optimize_configuration
    from freqtrade.enums import RunMode
    from freqtrade.optimize.backtesting import Backtesting

    from .runner import build_command

    nast = rec["settings"]
    cmd = build_command(python, profile, {**nast, "timeframe_detail": None})
    args = cmd[cmd.index("backtesting"):]
    args[args.index("--export") + 1] = "none"
    log("$ prepočet kresieb (Freqtrade, bez simulácie): " + " ".join(args))
    os.environ["TRADEBOT_PROFILE"] = str(profile)
    os.environ["TRADEBOT_DRAW_OUT"] = str(out)
    register()
    config = setup_optimize_configuration(Arguments(args).get_parsed_arg(), RunMode.BACKTEST)
    bt = Backtesting(config)
    data, _ = bt.load_bt_data()
    bt._set_strategy(bt.strategylist[0])
    bt.strategy.advise_all_indicators(data)
    runner = bt.strategy._runners.get(nast["pair"])
    return (runner.rows if runner is not None else {}), bt.strategy.ENTRY_TAG_PREFIX


def compute(store: Any, run_id: str, *, log: Callable[[str], None] = print,
            python: str | None = None) -> dict[str, Any]:
    """Prepočíta kresby behu do cache grafov a vráti výsledok kontroly (aj ho zapíše)."""
    from .. import engines
    from tradebot.core.types import INSTRUMENTS

    from .runner import effective_params, instrument_for_pair, run_multicharts, write_profile
    from .store import strategy_of

    t0 = time.time()
    rec = store.get(run_id)
    if rec is None:
        raise LookupError(f"beh {run_id} v histórii nie je")
    if rec.get("status") != "done":
        raise ValueError(f"beh {run_id} nedobehol ({rec.get('status')}) — graf nie je z čoho prepočítať")
    nast = dict(rec.get("settings") or {})
    if (nast.get("hyperopt") or {}).get("knobs"):
        raise ValueError("hyperopt nemá graf — kresby majú jeho overovacie behy")
    strategy = strategy_of(rec)
    inst_key = nast.get("instrument") or instrument_for_pair(nast["pair"])
    inst = INSTRUMENTS[inst_key]
    engine = nast.get("engine") or engines.FREQTRADE
    params = effective_params(rec.get("params") or {}, strategy)
    stored = store.trades(run_id)
    incomplete = _incomplete(rec)
    log(f"prepočet grafu {run_id}: {strategy} {nast.get('pair')} {nast.get('timeframe')} "
        f"{nast.get('timerange')} [{engine}]")
    for dovod in incomplete:
        log(f"POZOR: {dovod}")

    store.chart_cache.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=store.chart_cache))
    try:
        profile = write_profile(run_id, params, inst_key, strategy, directory=work)
        chart_tmp = work / "chart.json.gz"
        if engine == engines.MULTICHARTS:
            out = run_multicharts(params, nast, profile, log=log, chart_out=chart_tmp)
            _, rows, _, _ = out
            check = compare_trades(stored, rows)
        else:
            rows, prefix = _freqtrade_rows(rec, profile, chart_tmp, log, python or sys.executable)
            check = check_signals(stored, rows, prefix)
        if not chart_tmp.exists():
            raise RuntimeError("prepočet dobehol, ale kresby nevznikli")
        check.update(source="replay", engine=engine, incomplete=incomplete, created=_now(),
                     duration_s=round(time.time() - t0, 1))
        check["warning"] = _warning(check)
        store.put_chart(run_id, chart_tmp, check)
        log(f"hotovo za {check['duration_s']} s" + (f" — POZOR: {check['warning']}" if check["warning"] else ""))
        return check
    finally:
        import shutil

        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- #
# webapp: fronta prepočtov na pozadí
# --------------------------------------------------------------------------- #


@dataclass
class ReplayJob:
    run_id: str
    status: str = "queued"          # queued | running | failed (hotový je súbor v cache)
    created: str = field(default_factory=_now)
    started: str | None = None
    finished: str | None = None
    error: str | None = None
    log_lines: list[str] = field(default_factory=list)


class ChartReplayer:
    """Jedno pracovné vlákno, jeden prepočet naraz — nezávisle od fronty backtestov.

    `launcher(store, run_id, job)` urobí samotný prepočet; predvolený ho pustí ako podproces
    `python -m tester.webapp.replay`. Testy dosadia funkciu, ktorá beží vo vlákne.
    """

    def __init__(self, store: Any, python: str | None = None,
                 launcher: Callable[[Any, str, ReplayJob], None] | None = None) -> None:
        self.store = store
        self.python = python or sys.executable
        self.launcher = launcher or self._subprocess
        self.jobs: dict[str, ReplayJob] = {}
        self._q: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def status(self, run_id: str) -> dict[str, Any]:
        cesta = self.store.chart_file(run_id)
        if cesta is not None:
            check = self.store.chart_check(run_id) if cesta.parent == Path(self.store.chart_cache) else None
            return {"state": "ready", "source": (check or {}).get("source") or "legacy",
                    "warning": (check or {}).get("warning"), "check": check}
        job = self.jobs.get(run_id)
        if job is not None and job.status in ("queued", "running", "failed"):
            return {"state": job.status, "error": job.error, "log_tail": job.log_lines[-6:],
                    "started": job.started}
        return {"state": "missing"}

    def request(self, run_id: str) -> dict[str, Any]:
        """Zaradí prepočet, ak graf nie je ani sa nepočíta. Vráti stav."""
        with self._lock:
            stav = self.status(run_id)
            if stav["state"] in ("ready", "queued", "running"):
                return stav
            self.jobs[run_id] = ReplayJob(run_id)
            self._q.put(run_id)
        self._start()
        return self.status(run_id)

    def _start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, name="chart-replay", daemon=True)
            self._thread.start()

    def _loop(self) -> None:
        while True:
            run_id = self._q.get()
            job = self.jobs.get(run_id)
            if job is None or job.status != "queued":
                continue
            job.status, job.started = "running", _now()
            try:
                self.launcher(self.store, run_id, job)
                if self.store.chart_file(run_id) is None:
                    raise RuntimeError(job.error or "prepočet nevyrobil kresby")
                self.jobs.pop(run_id, None)       # hotové = súbor v cache
            except Exception as exc:  # noqa: BLE001 - chyba prepočtu nesmie zabiť vlákno
                job.status, job.error = "failed", str(exc)[-2000:]
                job.log_lines.append(traceback.format_exc()[-1500:])
            finally:
                job.finished = _now()

    def _subprocess(self, store: Any, run_id: str, job: ReplayJob) -> None:
        cmd = [self.python, "-m", "tester.webapp.replay", run_id,
               "--root", str(store.root), "--cache", str(store.chart_cache)]
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        env.pop("TRADEBOT_DRAW_OUT", None)
        proc = subprocess.Popen(cmd, cwd=str(REPO), env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                errors="replace", bufsize=1)
        assert proc.stdout is not None
        for line in proc.stdout:
            job.log_lines.append(line.rstrip("\n"))
            if len(job.log_lines) > 2000:
                del job.log_lines[:500]
        rc = proc.wait()
        if rc != 0:
            chyby = [l for l in job.log_lines if l.startswith("CHYBA")]
            raise RuntimeError((chyby[-1] if chyby else f"prepočet skončil s kódom {rc}"))


def main(argv: list[str] | None = None) -> int:
    import logging

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="python -m tester.webapp.replay", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id")
    ap.add_argument("--root", help="adresár histórie (default tester/runs)")
    ap.add_argument("--cache", help="cache grafov (default tester/runs/.charts)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    from .store import RunStore

    store = RunStore(Path(args.root) if args.root else None,
                     chart_cache=Path(args.cache) if args.cache else None)
    try:
        check = compute(store, args.run_id, log=lambda s: print(s, flush=True))
    except Exception as exc:  # noqa: BLE001
        print(traceback.format_exc(), flush=True)
        print(f"CHYBA: {exc}", flush=True)
        return 1
    print(json.dumps({k: check.get(k) for k in ("match", "warning", "duration_s")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
