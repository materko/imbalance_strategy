"""Porovnanie stratégie s C# jadrom proti jej Python predlohe — bar po bare, na rovnosť.

    python -m tester.compare.csharp_parity --exchange binance --from 2026-08-24 --to 2026-09-04
    python -m tester.compare.csharp_parity --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl.json \
        --from 2025-09-04 --to 2026-09-04 --set tradeDirection=Indicator --set indAdx=true

    python -m tester.compare.csharp_parity --runs 20260919-220413-134bdd 20260919-220445-9886a0

Oba enginy bežia v rovnakom `EngineRunner` (ten istý model vyplnenia, ten istý HTF feeder,
ten istý seeding), takže dostanú bit po bite rovnaké vstupy; na každom bare sa porovnajú
ordery, kresby, udalosti stavu, koniec seansy aj hodiny. Backtest povie „iný počet obchodov",
toto povie **na ktorom bare a v čom** sa enginy rozišli.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from tradebot.adapters.freqtrade.runner import EngineRunner
from tradebot.core import load_profile
from tradebot.core.candles import timeframe_minutes
from tradebot.core.types import Bar
from tradebot.core.warmup import seed_engine
from tradebot.strategies import get_spec

from .scan_zones import _load, _to_bar

__all__ = ["Mismatch", "compare", "compare_frames", "compare_runs", "main"]


def _plain(obj: Any) -> Any:
    """Objekt jadra -> porovnateľná štruktúra (dataclass podľa polí, enum podľa hodnoty)."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return {"__type__": type(obj).__name__.replace("CSharp", "").replace("IBS", ""),
                **{f.name: _plain(getattr(obj, f.name)) for f in fields(obj)}}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_plain(x) for x in obj]
    if isinstance(obj, (frozenset, set)):
        return sorted(_plain(x) for x in obj)
    if isinstance(obj, str):
        return str(obj)
    if isinstance(obj, float) and obj != obj:
        return "nan"  # NaN sa nerovná sám sebe
    return obj


class Mismatch(dict):
    """Jeden rozdiel: čas baru, čo sa líši, hodnota Pythonu a hodnota C#."""


def _diff(ts: int, what: str, py: Any, cs: Any, out: list[Mismatch]) -> None:
    a, b = _plain(py), _plain(cs)
    if a == b:
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(Mismatch(ts=ts, what=f"{what}: počet", python=len(a), csharp=len(b),
                                detail={"python": a, "csharp": b}))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                keys = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k)) if isinstance(x, dict) and isinstance(y, dict) else []
                out.append(Mismatch(ts=ts, what=f"{what}[{i}] {keys}", python=x, csharp=y))
        return
    out.append(Mismatch(ts=ts, what=what, python=a, csharp=b))


def _capture(runner: EngineRunner) -> list:
    """Zachytí výstup enginu na poslednom bare (runner ho inak spotrebuje sám)."""
    box: list = [None]
    original = runner.engine.on_bar

    def on_bar(bar, htf=None, ctx=None):
        box[0] = original(bar, htf, ctx)
        return box[0]

    runner.engine.on_bar = on_bar
    return box


def compare(python_key: str, csharp_key: str, profile: str, exchange: str, chart_tf: int,
            date_from: str | None = None, date_to: str | None = None,
            overrides: dict[str, Any] | None = None, max_mismatches: int = 20) -> dict[str, Any]:
    """Prehrá oba enginy nad sviečkami zo skladu (alebo Dukascopy CSV) a vráti súhrn + prvé rozdiely."""
    return compare_frames(python_key, csharp_key, profile, _load(exchange, f"{chart_tf}m"),
                          lambda tf: _load(exchange, tf), chart_tf, date_from, date_to, overrides, max_mismatches)


def compare_frames(python_key: str, csharp_key: str, profile: str, chart_all, htf_loader, chart_tf: int,
                   date_from: str | None = None, date_to: str | None = None,
                   overrides: dict[str, Any] | None = None, max_mismatches: int = 20) -> dict[str, Any]:
    """To isté nad hotovými DataFrame (`date` UTC, OHLCV, `ts` v ms); `htf_loader(tf)` dá informatívny TF."""
    import pandas as pd

    cfgs = {}
    for key in (python_key, csharp_key):
        cfg, inst = load_profile(profile, strategy=key)
        for name, value in (overrides or {}).items():
            setattr(cfg, name, value)
        cfg.validate()
        cfgs[key] = (cfg, inst)

    chart = chart_all
    if date_from:
        chart = chart[chart["date"] >= pd.Timestamp(date_from, tz="UTC")]
    if date_to:
        chart = chart[chart["date"] < pd.Timestamp(date_to, tz="UTC") + pd.Timedelta(days=1)]
    if chart.empty:
        raise SystemExit("v zadanom okne nie sú žiadne bary")

    runners: dict[str, EngineRunner] = {}
    boxes: dict[str, list] = {}
    seeded: dict[str, dict[str, int]] = {}
    first_ms = int(chart["ts"].iloc[0])
    for key, (cfg, inst) in cfgs.items():
        spec = get_spec(key)
        runner = EngineRunner(cfg, inst, chart_tf, spec=spec)
        if runner.htf is not None:
            htf_df = htf_loader(spec.informative_tfs(cfg)[0]).copy()
            htf_df["vol_sma"] = htf_df["volume"].rolling(cfg.volSmaLen).mean()
            runner.htf.load(
                {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)},
                {int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0) for r in htf_df.itertuples(index=False)},
            )
        seeded[key] = seed_engine(runner.engine, chart_all, first_ms)
        runners[key] = runner
        boxes[key] = _capture(runner)

    mismatches: list[Mismatch] = []
    counts = {"bars": 0, "orders": 0, "entries": 0, "drawings": 0, "events": 0}
    py, cs = runners[python_key], runners[csharp_key]
    last: Bar | None = None
    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        last = bar
        row_py = py.process(bar, py.htf.window_for(bar.time) if py.htf is not None else None)
        row_cs = cs.process(bar, cs.htf.window_for(bar.time) if cs.htf is not None else None)
        o_py, o_cs = boxes[python_key][0], boxes[csharp_key][0]
        counts["bars"] += 1
        counts["orders"] += len(o_py.orders)
        counts["entries"] += int(row_py.enter_long or row_py.enter_short)
        counts["drawings"] += len(o_py.drawings)
        counts["events"] += len(o_py.events)

        _diff(bar.time, "orders", o_py.orders, o_cs.orders, mismatches)
        _diff(bar.time, "drawings", o_py.drawings, o_cs.drawings, mismatches)
        _diff(bar.time, "events", o_py.events, o_cs.events, mismatches)
        _diff(bar.time, "close_session", o_py.close_session, o_cs.close_session, mismatches)
        _diff(bar.time, "clock", getattr(o_py, "clock", None), getattr(o_cs, "clock", None), mismatches)
        _diff(bar.time, "signal_row", row_py, row_cs, mismatches)
        if len(mismatches) >= max_mismatches:
            break

    if last is not None and len(mismatches) < max_mismatches:
        _diff(last.time, "final_drawings", py.engine.final_drawings(last), cs.engine.final_drawings(last), mismatches)

    return {"counts": counts, "seeded": seeded, "mismatches": mismatches[:max_mismatches],
            "required_history": {k: r.engine.required_history for k, r in runners.items()}}


def compare_runs(run_a: str, run_b: str) -> list[str]:
    """Dva behy z histórie (`tester/runs/<id>`) obchod po obchode; vráti zoznam rozdielov.

    `enter_tag` nesie prefix stratégie (`ibs:` / `ibsnet:`), preto sa porovnáva len čas
    baru signálu za dvojbodkou; všetko ostatné (časy, ceny, veľkosť, zisk, dôvod výstupu,
    stop, extrémy) musí sedieť presne.
    """
    import json

    from tradebot.core.paths import RUNS_DIR

    def load(run_id: str) -> list[dict]:
        trades = json.loads((RUNS_DIR / run_id / "trades.json").read_text(encoding="utf-8"))
        for t in trades:
            t["enter_tag"] = str(t.get("enter_tag", "")).split(":", 1)[-1]
        return trades

    a, b = load(run_a), load(run_b)
    diffs: list[str] = []
    if len(a) != len(b):
        diffs.append(f"počet obchodov: {len(a)} vs {len(b)}")
    for i, (x, y) in enumerate(zip(a, b), start=1):
        keys = sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
        if keys:
            diffs.append(f"obchod {i} ({x.get('open_date')}): " + ", ".join(f"{k} {x.get(k)!r} vs {y.get(k)!r}" for k in keys))
    return diffs


def _value(text: str) -> Any:
    low = text.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--python", default="ibs", help="kľúč Python stratégie (predloha)")
    ap.add_argument("--csharp", default="ibsnet", help="kľúč stratégie s C# jadrom")
    ap.add_argument("--profile", default="golden_binance_btcusdt_3m")
    ap.add_argument("--exchange", default="binance", help="kľúč burzy alebo cesta k Dukascopy CSV")
    ap.add_argument("--timeframe", default="3m")
    ap.add_argument("--from", dest="date_from")
    ap.add_argument("--to", dest="date_to")
    ap.add_argument("--set", action="append", default=[], metavar="POLE=HODNOTA")
    ap.add_argument("--max", type=int, default=20, help="po koľkých rozdieloch skončiť")
    ap.add_argument("--runs", nargs=2, metavar=("ID_PYTHON", "ID_CSHARP"),
                    help="namiesto prehratia enginov porovnaj dva hotové behy z histórie obchod po obchode")
    args = ap.parse_args(argv)

    if args.runs:
        diffs = compare_runs(*args.runs)
        print(f"{args.runs[0]} vs {args.runs[1]}: " + ("ZHODA obchod po obchode" if not diffs else f"{len(diffs)} rozdielov"))
        for d in diffs[: args.max]:
            print("  " + d)
        return 1 if diffs else 0

    overrides = {k: _value(v) for k, v in (item.split("=", 1) for item in args.set)}
    res = compare(args.python, args.csharp, args.profile, args.exchange, timeframe_minutes(args.timeframe),
                  args.date_from, args.date_to, overrides, args.max)
    c = res["counts"]
    print(f"{c['bars']} barov, {c['entries']} vstupov, {c['orders']} orderov, {c['events']} udalostí, "
          f"{c['drawings']} kresieb; seeding {res['seeded']}; predhistória {res['required_history']}")
    if not res["mismatches"]:
        print("ZHODA: C# jadro dáva na každom bare presne to isté ako Python engine")
        return 0
    print(f"ROZDIELY ({len(res['mismatches'])}):")
    for m in res["mismatches"]:
        print(f"  bar {m['ts']}  {m['what']}\n    python: {m['python']}\n    csharp: {m['csharp']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
