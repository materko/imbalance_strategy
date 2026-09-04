"""Prejde reálne dáta celým stavovým automatom a vypíše obchody — smoke test kroku 3.

    python -m ibs.tools.scan_trades --exchange binance --profile btcusdt_3m_binance

**Toto nie je backtest.** Vyplnenie orderov sa tu simuluje najjednoduchším možným
modelom (limitka sa vyplní, keď ju bar pretne; SL/TP sa vyhodnocujú na uzavretých
barech). Skutočné čísla dá až Freqtrade s `--timeframe-detail 1m`, kde sa rieši aj
otázka „trafil SL alebo TP skôr?" — viď ARCHITECTURE_port.md §7.

Zmysel tohto nástroja je iný: overiť, že stavový automat na reálnych dátach
prechádza stavmi, generuje ordre so zmysluplnými SL/TP a nikde sa nezasekne.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from ..core import (
    Bar,
    BarHistory,
    HTFWindow,
    IBSConfig,
    InstrumentSpec,
    MarketContext,
    OrderAction,
    SessionClock,
    StateMachine,
    ZoneBook,
    detect_sd_pattern,
    load_profile,
)
from ..core.risk import TradePlan
from ..core.types import Direction
from .scan_zones import _LAYOUT, _load, _to_bar


@dataclass
class SimTrade:
    """Jeden simulovaný obchod."""

    order_id: str
    direction: Direction
    plan: TradePlan
    placed_ms: int
    filled_ms: int | None = None
    closed_ms: int | None = None
    outcome: str = "PENDING"  # PENDING | FILLED | WIN | LOSS | EXPIRED | CANCELLED

    @property
    def is_open(self) -> bool:
        return self.outcome == "FILLED"


class NaiveFillSimulator:
    """Najjednoduchší možný model vyplnenia — zámerne, aby bolo jasné, čo ešte nie je."""

    def __init__(self) -> None:
        self.trades: dict[str, SimTrade] = {}
        self.position_size = 0.0

    @property
    def open_ids(self) -> frozenset[str]:
        return frozenset(t.order_id for t in self.trades.values() if t.is_open)

    def apply(self, intents, bar: Bar) -> None:
        for intent in intents:
            if intent.action is OrderAction.ENTRY and intent.plan is not None:
                self.trades[intent.order_id] = SimTrade(
                    order_id=intent.order_id,
                    direction=intent.plan.direction,
                    plan=intent.plan,
                    placed_ms=bar.time,
                )
            elif intent.action is OrderAction.CANCEL:
                t = self.trades.get(intent.order_id)
                if t is not None and t.outcome == "PENDING":
                    t.outcome = "EXPIRED" if intent.reason == "EXPIRED" else "CANCELLED"
                    t.closed_ms = bar.time

    def step(self, bar: Bar) -> None:
        for t in self.trades.values():
            if t.outcome == "PENDING":
                if bar.low <= t.plan.entry <= bar.high:
                    t.outcome = "FILLED"
                    t.filled_ms = bar.time
                    self.position_size = 1.0 if t.direction is Direction.LONG else -1.0
                continue

            if t.outcome != "FILLED":
                continue

            long = t.direction is Direction.LONG
            hit_sl = bar.low <= t.plan.stop_loss if long else bar.high >= t.plan.stop_loss
            hit_tp = bar.high >= t.plan.take_profit if long else bar.low <= t.plan.take_profit
            if hit_sl or hit_tp:
                # Ked bar trafi oboje, berieme SL - konzervativne. Realne rozhodnutie
                # patri 1m detailu vo Freqtrade.
                t.outcome = "LOSS" if hit_sl else "WIN"
                t.closed_ms = bar.time
                self.position_size = 0.0


def run(cfg: IBSConfig, inst: InstrumentSpec, exchange: str, chart_tf: int):
    htf_minutes = int(cfg.zoneDetectionTF)
    htf_ms = htf_minutes * 60_000

    chart = _load(exchange, f"{chart_tf}m")
    htf_df = _load(exchange, f"{htf_minutes}m")
    htf_df["vol_sma"] = htf_df["volume"].rolling(cfg.volSmaLen).mean().shift(1)

    htf_bars = {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)}
    htf_sma = {
        int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0)
        for r in htf_df.itertuples(index=False)
    }

    clock = SessionClock(cfg)
    book = ZoneBook(cfg, inst, chart_tf)
    machine = StateMachine(cfg, inst, book)
    history = BarHistory(maxlen=max(cfg.imbLookback, cfg.slLookback, cfg.volSmaLen) + 50)
    sim = NaiveFillSimulator()

    prev_htf_open: int | None = None
    transitions = 0
    reasons: dict[str, int] = {}

    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        history.append(bar)
        sim.step(bar)

        state = clock.state(bar.time)

        htf_open = bar.time // htf_ms * htf_ms
        if prev_htf_open is not None and htf_open != prev_htf_open and state.in_zone_window:
            opens = [htf_open - (i + 1) * htf_ms for i in range(HTFWindow.REQUIRED_BARS)]
            if all(o in htf_bars for o in opens):
                win = HTFWindow(tuple(htf_bars[o] for o in opens), htf_sma[opens[0]])
                pattern = detect_sd_pattern(win, cfg, inst)
                if pattern is not None:
                    zone = book.create_from_pattern(pattern, now_ms=bar.time)
                    if zone is not None:
                        zone.created_bar_index = history.bar_index
        prev_htf_open = htf_open

        ctx = MarketContext(
            in_trade_window=state.in_trade_window,
            position_size=sim.position_size,
            open_order_ids=sim.open_ids,
        )
        intents = machine.on_bar(bar, history, ctx)
        transitions += len(machine.events)
        for ev in machine.events:
            if ev.reason:
                # "gap @ 1234" zoskupime na "gap" - index baru je uzitocny v logu,
                # ale v suhrne by z neho bol zoznam jednotiek.
                key = ev.reason.split(" @ ")[0]
                reasons[key] = reasons.get(key, 0) + 1
        sim.apply(intents, bar)

    return book, sim, transitions, reasons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exchange", choices=sorted(_LAYOUT), default="binance")
    ap.add_argument("--profile", default="btcusdt_3m_binance")
    ap.add_argument("--chart-tf", type=int, default=3)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args(argv)

    cfg, inst = load_profile(args.profile)
    book, sim, transitions, reasons = run(cfg, inst, args.exchange, args.chart_tf)

    def fmt(ms: int | None) -> str:
        if ms is None:
            return "-"
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%m-%d %H:%M")

    counts: dict[str, int] = {}
    for t in sim.trades.values():
        counts[t.outcome] = counts.get(t.outcome, 0) + 1

    print(f"\nProfil {args.profile} na {args.exchange}, graf {args.chart_tf}m")
    print(f"  zon v evidencii:  {len(book)}")
    print(f"  prechodov stavov: {transitions}")
    print(f"  orderov:          {len(sim.trades)}")
    for outcome in ("WIN", "LOSS", "FILLED", "EXPIRED", "CANCELLED", "PENDING"):
        if counts.get(outcome):
            print(f"    {outcome:<10} {counts[outcome]}")

    wins, losses = counts.get("WIN", 0), counts.get("LOSS", 0)
    if wins + losses:
        print(f"  winrate:          {wins / (wins + losses) * 100:.0f}%  ({wins}W / {losses}L)")

    if reasons:
        print("\n  Preco zony skoncili:")
        for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"    {n:>4}x  {reason}")

    if sim.trades:
        print(f"\n  {'order':<10} {'zadany':<12} {'vyplneny':<12} {'entry':>10} {'SL':>10} {'TP':>10} {'qty':>8}  stav")
        for t in list(sim.trades.values())[-args.limit :]:
            p = t.plan
            print(
                f"  {t.order_id:<10} {fmt(t.placed_ms):<12} {fmt(t.filled_ms):<12} "
                f"{p.entry:>10.2f} {p.stop_loss:>10.2f} {p.take_profit:>10.2f} {p.qty:>8.3f}  {t.outcome}"
            )

    print(
        "\n  POZN: fill model je zamerne naivny (limitka sa vyplni, ked ju bar pretne)."
        "\n  Realne cisla da az Freqtrade s --timeframe-detail 1m.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
