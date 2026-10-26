"""Natívne behy C# stratégií na emulátore MultiCharts — pracovné procesy, súhrn ako história, behy bez histórie.

Jedno miesto pre všetko, čo počíta emulátor MultiCharts v C# (`csharp/TradeBot.Backtest`) namiesto
Python emulátora:

* `POOL` — pracovné procesy `TradeBot.Host.exe` (op `backtest`) zdieľané celým procesom (hyperopt,
  body sweepu/matice/okolia vo fronte webapp, `/api/native/backtests`). Každý proces drží 1m dáta
  a pripravené bary medzi behmi; procesy, nie vlákna, lebo .NET v procese Pythonu má len workstation GC
  a ten pri každom zbere zastaví všetky vlákna naraz.
* `NativeRunner` — dávka configov jednej stratégie na jednom trhu a TF, na jednom alebo viacerých oknách.
* `summary_of` / `record_of` — súhrn behu z obchodov C# tými istými funkciami ako Python emulátor
  (`rows_from_trades`, `summary_money`, `summarize`), takže čísla sa nemôžu rozísť s históriou.
* `run_record` — beh vo fronte webapp (bod celku bez kresieb) natívne; `can_run` povie, kedy smie.

Zhodu obchodov s Python emulátorom stráži `tester/tests/test_csharp_backtest.py`, súhrnov
`tester/tests/test_native_hyperopt.py`.
"""

from __future__ import annotations

import atexit
import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from tradebot.adapters.multicharts.emulator import EmulationResult, EmuTrade, rows_from_trades, summarize
from tradebot.core.money import summary_money
from tradebot.core.types import Direction, InstrumentSpec
from tradebot.strategies import get_spec

from . import engines

__all__ = ["POOL", "WorkerPool", "NativeRunner", "csharp_key", "window_ms", "window_days",
           "summary_of", "emulation_of", "can_run", "run_record", "instrument_json"]

#: Pracovný proces, ktorý toľko sekúnd nič nepočítal, sa pri ďalšom požičaní zavrie (drží stovky MB dát).
IDLE_SECONDS = 600


def csharp_key(strategy: str) -> str | None:
    """Kľúč C# jadra stratégie (`[TradeBotEngine("…")]`), alebo None, keď jadro v C# nemá."""
    return getattr(get_spec(strategy).engine_factory, "csharp_key", None)


def instrument_json(inst: InstrumentSpec) -> str:
    """Ten istý JSON inštrumentu, aký dostáva C# engine cez most (`CSharpEngine._open`)."""
    return json.dumps({
        "symbol": inst.symbol, "venue": inst.venue, "tick_size": inst.tick_size,
        "point_value": inst.point_value, "qty_step": inst.qty_step, "min_qty": inst.min_qty,
        "has_real_volume": inst.has_real_volume,
    })


def window_ms(timerange: str) -> tuple[int, int]:
    """`YYYYMMDD-YYYYMMDD` -> (od, do) v ms UTC; prázdna strana = -1 (bez hranice, ako v C#)."""
    a, _, b = (timerange or "").partition("-")

    def ms(text: str) -> int:
        if not text:
            return -1
        return int(datetime.strptime(text, "%Y%m%d").replace(tzinfo=timezone.utc).timestamp() * 1000)
    return ms(a), ms(b)


def window_days(timerange: str) -> int:
    a, b = window_ms(timerange)
    return max((b - a) // 86_400_000, 1) if a >= 0 and b >= 0 else 365


# --------------------------------------------------------------------------- #
# pracovné procesy
# --------------------------------------------------------------------------- #


#: Najdlhší jeden príkaz pracovného procesu (celý backtest / dávka bodov), s; `TRADEBOT_NATIVE_TIMEOUT`.
CALL_TIMEOUT = float(os.environ.get("TRADEBOT_NATIVE_TIMEOUT") or 3600)


class _Worker:
    """Jeden pracovný proces `TradeBot.Host.exe` (op `backtest`) — vlastný GC, dáta si drží medzi behmi."""

    def __init__(self) -> None:
        import subprocess

        from tradebot.adapters.csharp.bridge import _host_command
        from tradebot.core.paths import CSHARP_BIN

        from tradebot.adapters.csharp.bridge import LineReader

        self.proc = subprocess.Popen(_host_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     cwd=str(CSHARP_BIN), encoding="utf-8", bufsize=1)
        self._reader = LineReader(self.proc.stdout)
        self.last_used = time.time()

    @property
    def alive(self) -> bool:
        return self.proc.poll() is None

    def call(self, request: dict[str, Any]) -> dict[str, Any]:
        assert self.proc.stdin is not None and self.proc.stdout is not None
        try:
            self.proc.stdin.write(json.dumps(request) + "\n")
            self.proc.stdin.flush()
            line = self._reader.readline(CALL_TIMEOUT)
        except OSError as exc:
            return {"error": f"pracovný proces C# neodpovedá: {exc}"}
        finally:
            self.last_used = time.time()
        if line is None:
            # uviaznutý (nekonečná slučka, OOM): zabiť - pool mŕtvy proces pri vrátení zahodí a beh
            # skončí chybou, nie „running" naveky (audit N-WEB-10)
            self.proc.kill()
            return {"error": f"pracovný proces C# neodpovedal do {CALL_TIMEOUT / 60:.0f} min - zabitý"}
        if not line:
            return {"error": f"pracovný proces C# skončil (kód {self.proc.poll()})"}
        return json.loads(line)

    def close(self) -> None:
        try:
            if self.alive and self.proc.stdin is not None:
                self.proc.stdin.write(json.dumps({"op": "quit"}) + "\n")
                self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:  # noqa: BLE001 - zatvára sa na konci, nič sa už nezachráni
            self.proc.kill()


class WorkerPool:
    """Pracovné procesy zdieľané procesom: kto potrebuje N, požičia si ich a vráti.

    Strop je počet jadier (alebo `TRADEBOT_NATIVE_WORKERS`); keď sú všetky požičané, ďalší čaká.
    Mŕtvy proces sa pri vrátení zahodí, dlho nečinný sa pri požičaní zavrie.
    """

    def __init__(self, limit: int | None = None) -> None:
        self.limit = limit or int(os.environ.get("TRADEBOT_NATIVE_WORKERS") or 0) or (os.cpu_count() or 1)
        self._idle: list[_Worker] = []
        self._busy = 0
        self._cv = threading.Condition()

    def acquire(self, n: int) -> list[_Worker]:
        """Aspoň jeden, najviac `n` procesov (podľa toho, koľko je voľných pod stropom)."""
        n = max(1, min(int(n), self.limit))
        with self._cv:
            while self._busy >= self.limit:
                self._cv.wait()
            teraz = time.time()
            for w in [w for w in self._idle if teraz - w.last_used > IDLE_SECONDS]:
                self._idle.remove(w)
                w.close()
            pocet = min(n, self.limit - self._busy)
            out = [self._idle.pop() for _ in range(min(pocet, len(self._idle)))]
            self._busy += pocet
        try:
            while len(out) < pocet:
                out.append(_Worker())
        except Exception:
            self.release(out, failed=pocet - len(out))
            raise
        return out

    def release(self, workers: Iterable[_Worker], failed: int = 0) -> None:
        with self._cv:
            for w in workers:
                self._busy -= 1
                if w.alive:
                    self._idle.append(w)
            self._busy -= failed
            self._cv.notify_all()

    def stats(self) -> dict[str, int]:
        with self._cv:
            return {"limit": self.limit, "busy": self._busy, "idle": len(self._idle)}

    def close(self) -> None:
        with self._cv:
            idle, self._idle = self._idle, []
        for w in idle:
            w.close()


POOL = WorkerPool()
atexit.register(POOL.close)


# --------------------------------------------------------------------------- #
# dávky
# --------------------------------------------------------------------------- #


class NativeRunner:
    """Dávky backtestov jednej stratégie na jednom inštrumente a TF.

    `mode="processes"` (predvolené): pracovné procesy z `POOL`. `mode="threads"`: `NativeBacktest.RunBatchJson`
    v tomto procese cez pythonnet — bez štartu procesov, na pár behov a do testov (nad ~4 vláknami nezrýchľuje).
    """

    def __init__(self, strategy: str, inst: InstrumentSpec, timeframe: int, fee: float, threads: int = 0,
                 mode: str = "processes", pool: WorkerPool | None = None) -> None:
        self.spec = get_spec(strategy)
        self.key = csharp_key(strategy)
        if self.key is None:
            raise ValueError(f"{strategy}: stratégia nemá C# jadro — natívny beh nejde, použi Freqtrade alebo Python emulátor")
        if mode not in ("processes", "threads"):
            raise ValueError(f"neznámy režim {mode!r} (processes, threads)")
        self.inst = inst
        self.timeframe = int(timeframe)
        self.fee = float(fee)
        self.threads = int(threads)
        self.pool = pool or POOL
        self.workers = self.threads if self.threads > 0 else self.pool.limit
        self.mode = mode
        self.m1_path = engines.one_minute_file(inst)
        if not self.m1_path.exists():
            raise FileNotFoundError(f"chýbajú 1m dáta {self.m1_path}")
        self._inst_json = instrument_json(inst)
        self._native = None
        if mode == "threads":
            from tradebot.adapters.csharp import bridge

            bridge._load_clr()
            from TradeBot.Backtest import NativeBacktest

            self._native = NativeBacktest

    def run(self, configs: list[str], timerange: str) -> list[dict[str, Any]]:
        """Config JSON-y na jednom okne -> výsledky (`trades`, `bars`, …, alebo `error`) v tom istom poradí."""
        return self.run_many([(c, timerange) for c in configs])

    def run_many(self, tasks: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """(config JSON, okno) -> výsledok; všetky naraz na pracovných procesoch (aj rôzne okná v jednej dávke)."""
        if not tasks:
            return []
        if self._native is not None:
            from System import Array, String

            out: list[dict[str, Any]] = [{}] * len(tasks)
            for okno in dict.fromkeys(t for _c, t in tasks):
                a, b = window_ms(okno)
                idx = [i for i, (_c, t) in enumerate(tasks) if t == okno]
                raw = self._native.RunBatchJson(self.key, Array[String]([tasks[i][0] for i in idx]), self._inst_json,
                                                str(self.m1_path), self.timeframe, a, b, self.fee, self.threads)
                for i, r in zip(idx, raw):
                    out[i] = json.loads(r)
            return out

        workers = self.pool.acquire(min(self.workers, len(tasks)))
        out2: list[dict[str, Any] | None] = [None] * len(tasks)
        fronta = iter(range(len(tasks)))
        zamok = threading.Lock()

        def pracuj(w: _Worker) -> None:
            while True:
                with zamok:
                    i = next(fronta, None)
                if i is None:
                    return
                cfg, okno = tasks[i]
                a, b = window_ms(okno)
                out2[i] = w.call({"op": "backtest", "key": self.key, "config": cfg, "instrument": self._inst_json,
                                  "m1": str(self.m1_path), "tf": self.timeframe, "from": a, "to": b, "fee": self.fee})

        try:
            vlakna = [threading.Thread(target=pracuj, args=(w,), daemon=True) for w in workers]
            for t in vlakna:
                t.start()
            for t in vlakna:
                t.join()
        finally:
            self.pool.release(workers)
        return [r if r is not None else {"error": "beh sa nevykonal"} for r in out2]

    # spätná kompatibilita: runner mal kedysi vlastné procesy
    def close(self) -> None:
        pass

    def __enter__(self) -> "NativeRunner":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# súhrn
# --------------------------------------------------------------------------- #


def _trades(result: dict[str, Any]) -> list[EmuTrade]:
    return [EmuTrade(order_id=t["order_id"], direction=Direction.LONG if t["dir"] == 1 else Direction.SHORT,
                     qty=t["qty"], entry=t["entry"], open_ms=t["open_ms"], stop_initial=t["stop_initial"],
                     take_profit=t["take_profit"], market=t["market"], stop_last=t["stop_last"], exit=t["exit"],
                     close_ms=t["close_ms"], reason=t["reason"], max_price=t["max_price"], min_price=t["min_price"])
            for t in result["trades"]]


def summary_of(result: dict[str, Any], inst: InstrumentSpec, fee: float, wallet: float) -> dict[str, Any] | None:
    """Peňažný súhrn behu z obchodov C# — `rows_from_trades` + `summary_money`, ako história emulátora."""
    if "error" in result:
        return None
    return summary_money(rows_from_trades(_trades(result), inst, fee), wallet)


def emulation_of(result: dict[str, Any]) -> EmulationResult:
    """Výsledok C# v tvare Python emulátora (`emulate`) — pre `summarize` a `rows_from_trades`."""
    return EmulationResult(
        trades=_trades(result), bars=int(result["bars"]),
        first_ms=result["first_ms"] if result["bars"] else None, last_ms=result["last_ms"] if result["bars"] else None,
        first_close=result.get("first_close"), last_close=result.get("last_close"),
        ambiguous=int(result.get("ambiguous") or 0),
        daily_closes=[(int(d), float(c)) for d, c in result.get("daily") or []],
    )


def can_run(settings: dict[str, Any]) -> bool:
    """Smie beh vo fronte ísť natívne? Emulátor MultiCharts, stratégia s C# jadrom, bod celku (bez kresieb)
    a bez AI vrstvy. `TRADEBOT_NATIVE_BATCH=0` to vypne (pre porovnanie s Python emulátorom)."""
    from .webapp.batches import batch_tag

    if os.environ.get("TRADEBOT_NATIVE_BATCH", "1") in ("0", "false", "no"):
        return False
    if settings.get("engine") != engines.MULTICHARTS or batch_tag(settings) is None:
        return False
    if (settings.get("ai") or {}).get("enabled"):
        return False
    try:
        return csharp_key(settings.get("strategy") or "ibs") is not None
    except KeyError:
        return False


def run_record(params: dict[str, Any], settings: dict[str, Any], profile: Any, *,
               log: Callable[[str], None] = lambda _s: None):
    """Beh vo fronte webapp natívne — `(súhrn, obchody, séria, None)` ako `results.run_multicharts`."""
    from tradebot.core import load_profile
    from tradebot.core.candles import timeframe_minutes
    from tradebot.core.types import INSTRUMENTS

    from .webapp.market import instrument_for_pair

    inst = INSTRUMENTS[instrument_for_pair(settings["pair"])]
    cfg, _ = load_profile(profile, engine=engines.MULTICHARTS)
    tf = settings.get("timeframe") or "3m"
    fee = float(settings.get("fee") or 0.0)
    runner = NativeRunner(settings.get("strategy") or "ibs", inst, timeframe_minutes(tf), fee, threads=1)
    log(f"$ natívny emulátor MultiCharts (C#) {inst.exchange_symbol} {tf} {settings['timerange']}")
    res = runner.run([json.dumps(cfg.to_dict())], settings["timerange"])[0]
    if "error" in res:
        raise RuntimeError(f"natívny beh zlyhal: {res['error']}")
    if res.get("log"):
        for line in str(res["log"]).splitlines():
            log(line)
    result = emulation_of(res)
    wallet = float(settings.get("wallet") or 10000)
    rows = rows_from_trades(result.trades, inst, fee, float(params.get("leverage") or 1.0))
    summary, series = summarize(rows, wallet, result, currency=inst.quote_currency)
    summary["native"] = True
    return summary, rows, series, None
