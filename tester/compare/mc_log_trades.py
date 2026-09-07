"""Zoznam obchodov MultiCharts z logu študie (`%LOCALAPPDATA%/tradebot/multicharts.log`).

    python -m tester.compare.mc_log_trades                       # posledný beh v logu
    python -m tester.compare.mc_log_trades --from 2025-01-01 --to 2025-01-31
    python -m tester.compare.mc_log_trades --log C:/cesta/multicharts.log --json

MultiCharts x Python beta nevie zoznam obchodov exportovať zo študie; Strategy Performance
Report sa dá exportovať len ručne. Adaptér preto pri každom uzavretom obchode zapíše do
logu riadok `[trade] …` s tým, čo študia vidí (`TotalTrades`, `ClosedEquity`, posledný
vstupný order, loty, priemerná vstupná cena). Tento nástroj z toho spraví tabuľku, ktorá
sa dá položiť vedľa výstupu `scan_trades --csv` (offline simulátor) — to je celé
porovnanie MultiCharts vs. jadro.

Formát riadku (jeden obchod = jeden riadok, čas je bar grafu, na ktorom MultiCharts obchod
zaúčtoval, teda čas ZATVORENIA baru v UTC):

    HH:MM:SS [trade] n=<TotalTrades> bar=<YYYY-MM-DD HH:MM> order=<LONG_9> lots=<27> entry=<21674.909> pnl=<12.5> intrabar=<0|1>

`intrabar=1` = obchod sa otvoril aj zavrel vnútri jedného baru (pozícia na close nula);
vtedy MultiCharts nedá vstupnú cenu a `entry` je cena z plánu jadra.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

__all__ = ["McTrade", "parse_trades", "default_log_path"]

_TRADE = re.compile(
    r"\[trade\] n=(?P<n>\d+) bar=(?P<bar>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) order=(?P<order>\S+) "
    r"lots=(?P<lots>[\d.\-]+) entry=(?P<entry>[\d.\-]+|nan) pnl=(?P<pnl>[\d.\-]+) intrabar=(?P<intrabar>[01])"
)
_RUN_START = "prvy bar grafu"


@dataclass(frozen=True)
class McTrade:
    n: int
    bar: str
    order: str
    lots: float
    entry: float
    pnl: float
    intrabar: bool

    @property
    def outcome(self) -> str:
        return "WIN" if self.pnl > 0 else "LOSS" if self.pnl < 0 else "FLAT"


def default_log_path() -> Path:
    return Path(os.environ.get("TRADEBOT_MC_LOG") or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "tradebot" / "multicharts.log")


def parse_trades(lines, *, last_run_only: bool = True) -> list[McTrade]:
    """Riadky logu → obchody. `last_run_only` berie len časť po poslednom štarte študie."""
    lines = list(lines)
    if last_run_only:
        starts = [i for i, l in enumerate(lines) if _RUN_START in l]
        if starts:
            lines = lines[starts[-1]:]
    trades: list[McTrade] = []
    for line in lines:
        m = _TRADE.search(line)
        if not m:
            continue
        trades.append(McTrade(
            n=int(m["n"]), bar=m["bar"], order=m["order"], lots=float(m["lots"]),
            entry=float(m["entry"]), pnl=float(m["pnl"]), intrabar=m["intrabar"] == "1",
        ))
    return trades


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--log", type=Path, default=default_log_path())
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vratane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vratane")
    ap.add_argument("--all-runs", action="store_true", help="nie len posledny beh v logu")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if not args.log.exists():
        print(f"log neexistuje: {args.log}", file=sys.stderr)
        return 1
    with open(args.log, encoding="utf-8", errors="replace") as fh:
        trades = parse_trades(fh, last_run_only=not args.all_runs)
    if args.date_from:
        trades = [t for t in trades if t.bar[:10] >= args.date_from]
    if args.date_to:
        trades = [t for t in trades if t.bar[:10] <= args.date_to]

    if args.json:
        print(json.dumps([asdict(t) | {"outcome": t.outcome} for t in trades], indent=1))
        return 0
    wins = sum(t.pnl > 0 for t in trades)
    losses = sum(t.pnl < 0 for t in trades)
    print(f"MultiCharts obchody z {args.log.name}: {len(trades)}  ({wins}W / {losses}L, "
          f"PnL {sum(t.pnl for t in trades):.2f}, intrabar {sum(t.intrabar for t in trades)})")
    print(f"  {'#':>4} {'bar (UTC)':<17} {'order':<10} {'lots':>6} {'entry':>11} {'pnl':>10}  stav")
    for t in trades:
        print(f"  {t.n:>4} {t.bar:<17} {t.order:<10} {t.lots:>6g} {t.entry:>11.3f} {t.pnl:>10.2f}  "
              f"{t.outcome}{' (intrabar)' if t.intrabar else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
