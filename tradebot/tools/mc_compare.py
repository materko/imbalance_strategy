"""Porovnaj obchody MultiCharts (log študie) s offline simulátorom na tom istom Dukascopy CSV.

    python -m tradebot.tools.mc_compare --csv C:/dukas/NAS100_M1_10Y.csv \\
        --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-06 --to 2025-09-04

Simulátor beží priamo (`scan_trades.run`), obchody MultiCharts sa berú z `[trade]` riadkov
logu študie (`mc_log_trades`). Páruje sa hltavo podľa vstupnej ceny (do `--tolerance`
bodov) a blízkosti dátumu (MultiCharts hlási bar zavretia, simulátor čas zadania —
obchod môže trvať niekoľko dní). Výstup: koľko párov, koľko rovnakých výsledkov, a čo
ostalo len na jednej strane — to sú body na dohľadanie.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .mc_log_trades import McTrade, default_log_path, parse_trades

__all__ = ["SimTradeRow", "pair_trades", "CompareResult"]


@dataclass(frozen=True)
class SimTradeRow:
    order: str
    placed: datetime   # UTC
    entry: float
    qty: float
    outcome: str


@dataclass
class CompareResult:
    pairs: list[tuple[SimTradeRow, McTrade]]
    sim_only: list[SimTradeRow]
    mc_only: list[McTrade]

    @property
    def same_outcome(self) -> int:
        return sum(1 for s, m in self.pairs if s.outcome == m.outcome)


def _mc_time(t: McTrade) -> datetime:
    return datetime.strptime(t.bar, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


def pair_trades(sim: list[SimTradeRow], mc: list[McTrade], *, tolerance: float = 5.0,
                max_days: int = 10) -> CompareResult:
    """Hltavé párovanie: každý obchod simulátora dostane najbližší nespárovaný MultiCharts
    obchod s |entry| rozdielom do `tolerance`, ktorý sa zavrel najskôr v deň zadania a
    najneskôr `max_days` dní po ňom."""
    free = list(mc)
    pairs: list[tuple[SimTradeRow, McTrade]] = []
    sim_only: list[SimTradeRow] = []
    for s in sorted(sim, key=lambda r: r.placed):
        best = None
        for m in free:
            dt = _mc_time(m)
            if dt < s.placed.replace(hour=0, minute=0) or dt > s.placed + timedelta(days=max_days):
                continue
            diff = abs(m.entry - s.entry)
            if diff > tolerance:
                continue
            key = (diff, dt)
            if best is None or key < best[0]:
                best = (key, m)
        if best is None:
            sim_only.append(s)
        else:
            free.remove(best[1])
            pairs.append((s, best[1]))
    return CompareResult(pairs=pairs, sim_only=sim_only, mc_only=free)


def _sim_rows(csv: Path, profile: str, chart_tf: int, date_from: str, date_to: str) -> list[SimTradeRow]:
    from ..core import load_profile
    from .scan_trades import run

    cfg, inst = load_profile(profile)
    _book, sim, _t, _r = run(cfg, inst, csv, chart_tf, date_from, date_to)
    start = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
    rows = []
    for t in sim.trades.values():
        placed = datetime.fromtimestamp(t.placed_ms / 1000, tz=timezone.utc)
        if placed < start or t.outcome not in ("WIN", "LOSS"):
            continue
        rows.append(SimTradeRow(order=t.order_id, placed=placed, entry=t.plan.entry, qty=t.plan.qty, outcome=t.outcome))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", type=Path, required=True, help="Dukascopy 1m CSV (to isté, čo má MultiCharts)")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--chart-tf", type=int, default=3)
    ap.add_argument("--from", dest="date_from", required=True)
    ap.add_argument("--to", dest="date_to", required=True)
    ap.add_argument("--log", type=Path, default=default_log_path())
    ap.add_argument("--tolerance", type=float, default=5.0, help="max rozdiel entry v bodoch")
    args = ap.parse_args(argv)

    with open(args.log, encoding="utf-8", errors="replace") as fh:
        mc = [t for t in parse_trades(fh) if args.date_from <= t.bar[:10] <= args.date_to]
    sim = _sim_rows(args.csv, args.profile, args.chart_tf, args.date_from, args.date_to)
    res = pair_trades(sim, mc, tolerance=args.tolerance)

    print(f"okno {args.date_from}..{args.date_to}: simulator {len(sim)} vyplnenych, MultiCharts {len(mc)}; "
          f"sparovanych {len(res.pairs)}, rovnaky vysledok {res.same_outcome}")
    print("\n-- rozdielny vysledok v pare (sim -> MC):")
    for s, m in res.pairs:
        if s.outcome != m.outcome:
            print(f"  {s.placed:%Y-%m-%d %H:%M} {s.order:<10} entry {s.entry:.3f} qty {s.qty:g}: sim {s.outcome} / MC {m.outcome}"
                  f" (MC {m.order}, entry {m.entry:.3f}, pnl {m.pnl:.2f}{', intrabar' if m.intrabar else ''})")
    print("\n-- len v simulatore:")
    for s in res.sim_only:
        print(f"  {s.placed:%Y-%m-%d %H:%M} {s.order:<10} entry {s.entry:.3f} qty {s.qty:g} {s.outcome}")
    print("\n-- len v MultiCharts:")
    for m in res.mc_only:
        print(f"  {m.bar} {m.order:<10} entry {m.entry:.3f} lots {m.lots:g} {m.outcome}{' intrabar' if m.intrabar else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
