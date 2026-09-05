"""Fronta a spúšťanie Freqtrade backtestu v podprocese.

Jeden beh naraz: Freqtrade s `--timeframe-detail 1m` vyťaží jedno jadro a dva
paralelné behy by si len prekážali (a hlavne by sa nedalo povedať, ktorý zip
v `backtest_results/` patrí ktorému). Ostatné behy čakajú vo fronte.

Parametre stratégie idú do Freqtradu cez dočasný JSON profil a premennú
`IBS_PROFILE` — presne tak, ako to robí stratégia pri ručnom spúšťaní. Nastavenia
behu (pár, obdobie, poplatok, peňaženka, 1m detail) idú cez CLI prepínače.

Cez `IBS_DRAW_OUT` si beh vypýta od stratégie aj kresby enginu (zóny, TP/SL boxy,
štítky…) — po dobehnutí sa presunú do adresára behu ako `chart.json.gz` a detail
behu z nich kreslí graf páru.
"""

from __future__ import annotations

import json
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

from ..core import IBSConfig, load_profile
from ..core.config import CONFIG_DIR
from ..core.types import INSTRUMENTS
from .store import RunStore, make_run_id

REPO = Path(__file__).resolve().parents[2]
FT_DIR = REPO / "platforms" / "freqtrade"
USER_DIR = FT_DIR / "user_data"
RESULTS_DIR = USER_DIR / "backtest_results"
DATA_DIR = USER_DIR / "data" / "binance" / "futures"
TMP_PROFILES = USER_DIR / "runs" / ".profiles"

#: Koľko riadkov logu sa uloží k behu — celý log Freqtradu má stovky riadkov
#: o načítavaní dát, ktoré nikoho nezaujímajú.
LOG_KEEP_LINES = 400


def instrument_for_pair(pair: str) -> str:
    for key, inst in INSTRUMENTS.items():
        if inst.symbol == pair:
            return key
    raise ValueError(f"pre pár {pair!r} nie je definovaný InstrumentSpec (ibs/core/types.py)")


def available_pairs() -> list[dict[str, Any]]:
    """Páry, pre ktoré sú stiahnuté 3m dáta, a ich dátumový rozsah."""
    import pandas as pd

    out = []
    for p in sorted(DATA_DIR.glob("*-3m-futures.feather")):
        base = p.name.split("-3m-")[0]  # BTC_USDT_USDT
        parts = base.split("_")
        if len(parts) != 3:
            continue
        pair = f"{parts[0]}/{parts[1]}:{parts[2]}"
        try:
            instrument_for_pair(pair)
        except ValueError:
            continue
        dates = pd.read_feather(p, columns=["date"])["date"]
        detail = (p.parent / p.name.replace("-3m-", "-1m-")).exists()
        htf = (p.parent / p.name.replace("-3m-", "-5m-")).exists()
        from .chart import available_timeframes

        out.append({
            "pair": pair,
            "instrument": instrument_for_pair(pair),
            "from": str(dates.min())[:10],
            "to": str(dates.max())[:10],
            "bars_3m": int(len(dates)),
            "has_1m": detail,
            "has_5m": htf,
            "timeframes": available_timeframes(pair),
        })
    return out


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

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id, "status": self.status, "created": self.created, "started": self.started,
            "finished": self.finished, "error": self.error, "settings": self.settings,
            "note": self.note, "user": self.user, "log_tail": self.log_lines[-40:],
        }


def tf_minutes(tf: str) -> int:
    """`3m` → 3, `1h` → 60, `1d` → 1440."""
    unit = tf[-1]
    n = int(tf[:-1])
    return n * {"m": 1, "h": 60, "d": 1440}[unit]


def build_command(python: str, profile_path: Path, settings: dict[str, Any]) -> list[str]:
    """`timeframe` je TF grafu, na ktorom stratégia počíta (ako TF grafu v TradingView);
    Freqtrade ním prebije `timeframe` stratégie. 1m detail má zmysel len pod ním."""
    tf = settings.get("timeframe") or "3m"
    cmd = [
        python, "-m", "freqtrade", "backtesting",
        "--config", str(FT_DIR / "config.binance.json"),
        "--userdir", str(USER_DIR),
        "--strategy", "IBSImbalanceStrategy",
        "--cache", "none",
        "--export", "trades",
        "--timerange", settings["timerange"],
        "--pairs", settings["pair"],
        "--timeframe", tf,
        "--dry-run-wallet", str(settings.get("wallet", 10000)),
    ]
    if settings.get("fee") is not None:
        cmd += ["--fee", str(settings["fee"])]
    detail = settings.get("timeframe_detail", "1m")
    if detail and tf_minutes(detail) < tf_minutes(tf):
        cmd += ["--timeframe-detail", detail]
    return cmd


def write_profile(run_id: str, params: dict[str, Any], instrument: str) -> Path:
    """Dočasný profil pre `IBS_PROFILE`. Validácia configu tu spadne skôr než Freqtrade."""
    cfg = IBSConfig.from_dict({k: v for k, v in params.items() if not k.startswith("_")})
    data = cfg.to_dict()
    data["_instrument"] = instrument
    data["_comment"] = [f"docasny profil behu {run_id} (webapp) - negeneruj rucne"]
    TMP_PROFILES.mkdir(parents=True, exist_ok=True)
    path = TMP_PROFILES / f"{run_id}.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path


# --------------------------------------------------------------------------- #
# Spracovanie výsledku
# --------------------------------------------------------------------------- #

_TRADE_COLS = (
    "open_date", "close_date", "open_rate", "close_rate", "amount", "stake_amount", "leverage",
    "profit_abs", "profit_ratio", "exit_reason", "enter_tag", "is_short", "fee_open", "fee_close",
    "funding_fees", "trade_duration", "initial_stop_loss_abs", "stop_loss_abs", "max_rate", "min_rate",
)


def result_from_zip(zip_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """(súhrn, obchody, série pre graf) z výsledkového zipu Freqtradu."""
    import pandas as pd

    from ..tools.report import load

    stats, trades, change = load(zip_path)
    start = float(stats["starting_balance"])

    gross = volume = 0.0
    if not trades.empty:
        d = trades["is_short"].map({True: -1.0, False: 1.0})
        gross = float(((trades["close_rate"] - trades["open_rate"]) * trades["amount"] * d).sum())
        volume = float(((trades["open_rate"] + trades["close_rate"]) * trades["amount"]).sum())

    exits = {}
    if not trades.empty:
        for reason, g in trades.groupby("exit_reason"):
            exits[str(reason)] = {"n": int(len(g)), "pnl_abs": round(float(g["profit_abs"].sum()), 2)}

    summary = {
        "trades": int(stats["total_trades"]),
        "wins": int(stats["wins"]), "losses": int(stats["losses"]), "draws": int(stats.get("draws", 0)),
        "winrate": round(100.0 * stats["wins"] / stats["total_trades"], 2) if stats["total_trades"] else 0.0,
        "pnl_abs": round(float(stats["profit_total_abs"]), 2),
        "pnl_pct": round(float(stats["profit_total"]) * 100.0, 3),
        "profit_factor": round(float(stats.get("profit_factor") or 0.0), 3),
        "max_drawdown_abs": round(float(stats.get("max_drawdown_abs", 0.0)), 2),
        "max_drawdown_pct": round(float(stats.get("max_drawdown_account", 0.0)) * 100.0, 3),
        "starting_balance": start,
        "final_balance": round(float(stats.get("final_balance", start)), 2),
        "stake_currency": stats.get("stake_currency", "USDT"),
        "gross_abs": round(gross, 2),
        "volume_abs": round(volume, 2),
        "break_even_pct": round(gross / volume * 100.0, 4) if volume else None,
        "market_change_pct": round(float(stats.get("market_change", 0.0)) * 100.0, 3),
        "backtest_start": stats.get("backtest_start"),
        "backtest_end": stats.get("backtest_end"),
        "holding_avg": str(stats.get("holding_avg", "")),
        "exits": exits,
    }

    rows: list[dict[str, Any]] = []
    if not trades.empty:
        t = trades.sort_values("close_date")
        for r in t.to_dict("records"):
            row = {k: r.get(k) for k in _TRADE_COLS if k in r}
            for k in ("open_date", "close_date"):
                if row.get(k) is not None:
                    row[k] = pd.Timestamp(row[k]).isoformat()
            for k, v in list(row.items()):
                if hasattr(v, "item"):
                    row[k] = v.item()
            rows.append(row)

    series: dict[str, Any] = {"equity": [], "market": []}
    if not trades.empty:
        t = trades.sort_values("close_date")
        pct = (t["profit_abs"] / start * 100.0)
        series["equity"] = [
            [pd.Timestamp(ts).isoformat(), round(float(p), 4), round(float(c), 4)]
            for ts, p, c in zip(t["close_date"], pct, pct.cumsum())
        ]
    if change is not None and not change.empty:
        bh = change.set_index("date")["rel_mean"].resample("1D").last().dropna()
        series["market"] = [[pd.Timestamp(ts).isoformat(), round(float(v) * 100.0, 4)] for ts, v in bh.items()]

    return summary, rows, series


# --------------------------------------------------------------------------- #
# Worker
# --------------------------------------------------------------------------- #


class BacktestRunner:
    """Fronta jedného pracovného vlákna. `submit()` vráti Job, výsledok skončí v store."""

    def __init__(self, store: RunStore, python: str | None = None,
                 command_builder: Callable[[str, Path, dict[str, Any]], list[str]] = build_command) -> None:
        self.store = store
        self.python = python or sys.executable
        self.build_command = command_builder
        self.jobs: dict[str, Job] = {}
        self.order: list[str] = []
        self._q: "queue.Queue[str]" = queue.Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._loop, name="ibs-backtest-worker", daemon=True)
            self._thread.start()

    def submit(self, params: dict[str, Any], settings: dict[str, Any], note: str = "", user: str = "") -> Job:
        # config sa validuje HNEĎ, aby tester dostal chybu do formulára a nie do logu behu
        IBSConfig.from_dict({k: v for k, v in params.items() if not k.startswith("_")})
        instrument_for_pair(settings["pair"])
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
            job.proc.kill()
            return True
        return False

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self.jobs[i].public() for i in self.order if self.jobs[i].status in ("queued", "running")]

    def job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    # -- vnútro ------------------------------------------------------------ #

    def _loop(self) -> None:
        while True:
            job_id = self._q.get()
            job = self.jobs.get(job_id)
            if job is None or job.status != "queued":
                continue
            try:
                self._run(job)
            except Exception:  # noqa: BLE001 - chyba behu nesmie zabiť worker
                job.status = "failed"
                job.error = traceback.format_exc()[-2000:]
                job.finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
                self._persist(job, None)

    def _run(self, job: Job) -> None:
        job.status = "running"
        job.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        t0 = time.time()
        instrument = instrument_for_pair(job.settings["pair"])
        profile = write_profile(job.id, job.params, instrument)
        cmd = self.build_command(self.python, profile, job.settings)
        job.log_lines.append("$ " + " ".join(cmd))

        chart_tmp = TMP_PROFILES / f"{job.id}.chart.json.gz"
        env = dict(os.environ, IBS_PROFILE=str(profile), IBS_DRAW_OUT=str(chart_tmp),
                   PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        before = {p.name for p in RESULTS_DIR.glob("*.zip")} if RESULTS_DIR.exists() else set()

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
            (p for p in RESULTS_DIR.glob("*.zip") if p.name not in before),
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
        job.status = "done"
        self._persist(job, (summary, trades, series), duration, chart_path=chart_tmp)

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


def default_params(profile: str | None = None) -> tuple[dict[str, Any], str | None]:
    """Parametre formulára: Pine defaulty, alebo profil z `ibs/configs/`."""
    if profile:
        cfg, inst = load_profile(profile)
        key = next(k for k, v in INSTRUMENTS.items() if v is inst)
        return cfg.to_dict(), key
    return IBSConfig().to_dict(), None


def list_profiles() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))
