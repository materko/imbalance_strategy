"""Natívny C# backtest (`tradebot/core/csharp/TradeBot.Backtest`) proti Python emulátoru MultiCharts — obchod po obchode.

    python -m tester.compare.csharp_backtest --strategy orbnet --instrument nas100_dukascopy \
        --timeframe 3m --from 2025-01-01 --to 2025-04-01
    python -m tester.compare.csharp_backtest --strategy ibsnet --profile golden_binance_btcusdt_3m \
        --instrument btcusdt_binance --from 2026-06-01 --to 2026-08-01 --set maxDailyWins=2

Obe strany dostanú ten istý profil a ten istý 1m súbor (`tester.engines.one_minute_file`).
Python ide cestou webapp (`emulate` s C# enginom cez most), C# číta feather sám, skladá TF,
seeduje predhistóriu a emuluje brokera bez Pythonu. Zhoda znamená rovnaké obchody na bit:
order, smer, množstvo, vstup a výstup (cena aj minúta), SL/TP, dôvod, extrémy.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

from tradebot.core import load_profile
from tradebot.core.candles import timeframe_minutes
from tradebot.core.types import INSTRUMENTS, Direction, InstrumentSpec
from tradebot.strategies import get_spec

from .. import engines

__all__ = ["instrument_json", "run_python", "run_csharp", "compare_trades", "main"]

#: Polia obchodu, ktoré sa porovnávajú na rovnosť (názvy z JSON C# strany).
FIELDS = ("order_id", "dir", "qty", "entry", "open_ms", "stop_initial", "take_profit", "market",
          "stop_last", "exit", "close_ms", "reason", "max_price", "min_price")


def instrument_json(inst: InstrumentSpec) -> str:
    """Ten istý JSON inštrumentu, aký dostáva C# engine cez most (`CSharpEngine._open`)."""
    return json.dumps({
        "symbol": inst.symbol, "venue": inst.venue, "tick_size": inst.tick_size,
        "point_value": inst.point_value, "qty_step": inst.qty_step, "min_qty": inst.min_qty,
        "has_real_volume": inst.has_real_volume,
    })


def _cfg(strategy: str, profile: str | None, sets: dict[str, Any]):
    spec = get_spec(strategy)
    cfg, _ = load_profile(profile or spec.default_profile, strategy=spec.key, engine=engines.MULTICHARTS)
    if sets:
        cfg = type(cfg).from_dict({**cfg.to_dict(), **sets})
    return spec, cfg


def run_python(strategy: str, profile: str | None, inst: InstrumentSpec, tf: int, from_ms: int | None,
               to_ms: int | None, fee: float, sets: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Python emulátor (cesta webapp `run_multicharts`) — obchody v tvare C# JSON."""
    import pandas as pd

    from tradebot.adapters.multicharts.emulator import emulate

    spec, cfg = _cfg(strategy, profile, sets or {})
    m1 = pd.read_feather(engines.one_minute_file(inst))
    result, _runner = emulate(cfg, inst, m1, tf, from_ms=from_ms, to_ms=to_ms, fee=fee, spec=spec)
    return [{
        "order_id": t.order_id, "dir": 1 if t.direction is Direction.LONG else -1, "qty": t.qty,
        "entry": t.entry, "open_ms": t.open_ms, "stop_initial": t.stop_initial, "take_profit": t.take_profit,
        "market": t.market, "stop_last": t.stop_last, "exit": t.exit, "close_ms": t.close_ms,
        "reason": t.reason, "max_price": t.max_price, "min_price": t.min_price,
    } for t in result.trades]


def run_csharp(strategy: str, profile: str | None, inst: InstrumentSpec, tf: int, from_ms: int | None,
               to_ms: int | None, fee: float, sets: dict[str, Any] | None = None) -> dict[str, Any]:
    """Natívny C# backtest — `NativeBacktest.RunFileJson`."""
    from tradebot.adapters.csharp import bridge

    bridge._load_clr()
    from TradeBot.Backtest import NativeBacktest

    spec, cfg = _cfg(strategy, profile, sets or {})
    key = getattr(spec.engine_factory, "csharp_key", None)
    if key is None:
        raise SystemExit(f"{strategy}: stratégia nemá C# jadro")
    raw = NativeBacktest.RunFileJson(key, json.dumps(cfg.to_dict()), instrument_json(inst),
                                     str(engines.one_minute_file(inst)), int(tf),
                                     -1 if from_ms is None else int(from_ms), -1 if to_ms is None else int(to_ms),
                                     float(fee))
    return json.loads(raw)


def compare_trades(py: list[dict[str, Any]], cs: list[dict[str, Any]]) -> list[str]:
    """Rozdiely ako vety (prázdny zoznam = zhoda). Po prvom rozchode sa ďalej neporovnáva."""
    out: list[str] = []
    for i, (a, b) in enumerate(zip(py, cs)):
        diff = [f"{k}: python={a.get(k)!r} csharp={b.get(k)!r}" for k in FIELDS if a.get(k) != b.get(k)]
        if diff:
            when = datetime.fromtimestamp(a["open_ms"] / 1000, tz=timezone.utc).isoformat()
            out.append(f"obchod {i} ({a['order_id']} {when}): " + "; ".join(diff))
            return out
    if len(py) != len(cs):
        out.append(f"počet obchodov: python={len(py)} csharp={len(cs)}")
    return out


def _ms(day: str | None) -> int | None:
    if not day:
        return None
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--profile")
    ap.add_argument("--instrument", required=True, help="kľúč z tradebot.core.types.INSTRUMENTS")
    ap.add_argument("--timeframe", help="default = TF stratégie")
    ap.add_argument("--from", dest="from_day")
    ap.add_argument("--to", dest="to_day")
    ap.add_argument("--fee", type=float, default=0.0)
    ap.add_argument("--set", action="append", default=[], metavar="POLE=HODNOTA")
    a = ap.parse_args(argv)

    sets = {k: json.loads(v) if v[:1] in "[{0123456789-tfn\"" else v
            for k, v in (s.split("=", 1) for s in a.set)}
    spec = get_spec(a.strategy)
    tf = timeframe_minutes(a.timeframe or spec.default_timeframe)
    inst = INSTRUMENTS[a.instrument]
    args = (a.strategy, a.profile, inst, tf, _ms(a.from_day), _ms(a.to_day), a.fee, sets)

    t0 = time.perf_counter()
    py = run_python(*args)
    t1 = time.perf_counter()
    cs = run_csharp(*args)
    t2 = time.perf_counter()
    print(cs["log"])
    print(f"python emulator: {len(py)} obchodov za {t1 - t0:.1f} s; C# natívne: {len(cs['trades'])} obchodov "
          f"za {t2 - t1:.1f} s ({cs['bars']} barov)")
    diff = compare_trades(py, cs["trades"])
    for line in diff:
        print("ROZDIEL", line)
    if not diff:
        print("ZHODA: obchody sú bit po bite rovnaké")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
