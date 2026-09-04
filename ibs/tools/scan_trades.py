"""Prejde reálne dáta celým stavovým automatom a vypíše obchody — smoke test kroku 3.

    python -m ibs.tools.scan_trades --exchange binance --profile btcusdt_3m_binance

Signály generuje engine na uzavretých barech grafu (3m). Vyplnenie a výstupy sa
prehrávajú po **1m** sviečkach vnútri každého 3m baru — rovnaký princíp ako
`--timeframe-detail 1m` vo Freqtrade (ARCHITECTURE_port.md §7). Vďaka tomu sa
korektne rozhodne aj otázka „trafil SL alebo TP skôr?".

Nástroj je nutný pre **Coinbase**: Freqtrade tam backtest spustiť nevie (burzu
nepodporuje a 3m sviečky neponúka), ale referenčné screenshoty sú práve odtiaľ.
Ak 1m dáta chýbajú, prepne sa na hrubší model na 3m baroch a napíše to.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from ..core import (
    htf_window_opens,
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
from ..core.risk import TradePlan, extreme_before_stop
from ..core.types import Direction
from .scan_zones import _LAYOUT, _load, _to_bar


def _utc_day(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


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
    #: Najlepšia cena od vstupu — z nej sa počíta trailing stop.
    extreme: float = float("nan")
    #: Cena, za ktorú sa obchod naozaj zavrel. Pri vypnutom trailingu je to vždy
    #: `plan.take_profit` alebo `plan.stop_loss`; s trailingom to môže byť čokoľvek
    #: medzi tým, takže sa to musí pamätať zvlášť.
    exit_price: float = float("nan")

    @property
    def is_open(self) -> bool:
        return self.outcome == "FILLED"


class FillSimulator:
    """Vyplnenie a výstupy. Ak sú k dispozícii 1m sviečky, prehráva sa nimi.

    Bez 1m detailu je bar, ktorý pretne SL aj TP, nejednoznačný a museli by sme hádať;
    s 1m detailom sa proste pozrieme, ktorý prišiel skôr.
    """

    def __init__(self) -> None:
        self.trades: dict[str, SimTrade] = {}
        self.position_size = 0.0
        self.daily_wins: dict[str, int] = {}
        self.ambiguous_bars = 0

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

    def step(self, bar: Bar, detail: list[Bar] | None = None) -> None:
        """`detail` sú 1m sviečky vnútri tohto baru; bez nich sa použije samotný bar."""
        for sub in detail or [bar]:
            self._step_one(sub, ambiguous_ok=detail is None)

    def _step_one(self, bar: Bar, *, ambiguous_ok: bool) -> None:
        for t in self.trades.values():
            if t.outcome == "PENDING":
                if bar.low <= t.plan.entry <= bar.high:
                    t.outcome = "FILLED"
                    t.filled_ms = bar.time
                    t.extreme = t.plan.entry
                    self.position_size = 1.0 if t.direction is Direction.LONG else -1.0
                continue

            if t.outcome != "FILLED":
                continue

            long = t.direction is Direction.LONG
            stop = t.plan.stop_loss
            if t.plan.trailing is None:
                hit_sl = bar.low <= stop if long else bar.high >= stop
            else:
                stop, hit_sl = self._trailing(t, bar, long)

            hit_tp = bar.high >= t.plan.take_profit if long else bar.low <= t.plan.take_profit
            if not (hit_sl or hit_tp):
                continue

            if hit_sl and hit_tp:
                # Aj na 1m sa to este moze stat - vtedy je to naozaj nerozhodnutelne
                # a berieme SL (konzervativne), ale spocitame to.
                if ambiguous_ok:
                    self.ambiguous_bars += 1
                t.exit_price = stop
            else:
                t.exit_price = stop if hit_sl else t.plan.take_profit

            # O výsledku rozhoduje cena, nie ktorý príkaz vyplnil: trailing stop nad
            # vstupom je zisk, hoci ho poslal stop order.
            gain = (t.exit_price - t.plan.entry) if long else (t.plan.entry - t.exit_price)
            t.outcome = "WIN" if gain > 0 else "LOSS"

            t.closed_ms = bar.time
            self.position_size = 0.0
            if t.outcome == "WIN":
                day = _utc_day(bar.time)
                self.daily_wins[day] = self.daily_wins.get(day, 0) + 1

    @staticmethod
    def _trailing(t: SimTrade, bar: Bar, long: bool) -> tuple[float, bool]:
        """(stop na tomto bare, či sa trafil) — s poradím pohybu vnútri sviečky.

        Broker emulátor v TradingView prejde bar v poradí open → bližší extrém →
        vzdialenejší extrém → close. Pri trailingu to nie je kozmetika:

        * **priaznivý extrém prvý** — trailing sa posunie hore a stop sa až potom
          testuje proti nepriaznivej strane;
        * **nepriaznivý extrém prvý** — najprv sa testuje ešte STARÝ stop, potom sa
          trailing posunie a testuje sa spiatočná noha bar → `close`.

        Tá druhá vetva je dôvod, prečo sa tu pozerá aj na `close`. Bez nej vyjde raz
        výstup priskoro (bar, kde cena najprv klesla a až potom vyletela) a inokedy
        vôbec (bar, kde sa cena po extréme vrátila pod trailing ešte pred zatvorením).
        """
        tr = t.plan.trailing
        best = bar.high if long else bar.low
        after = max(t.extreme, best) if long else min(t.extreme, best)
        before_stop = tr.stop_price(t.direction, t.plan.entry, t.plan.stop_loss, t.extreme)
        after_stop = tr.stop_price(t.direction, t.plan.entry, t.plan.stop_loss, after)
        t.extreme = after

        if extreme_before_stop(bar.open, bar.high, bar.low, long=long):
            hit = bar.low <= after_stop if long else bar.high >= after_stop
            return after_stop, hit

        if (bar.low <= before_stop) if long else (bar.high >= before_stop):
            return before_stop, True
        hit = bar.close <= after_stop if long else bar.close >= after_stop
        return after_stop, hit

    def wins_today(self, ts_ms: int) -> int:
        return self.daily_wins.get(_utc_day(ts_ms), 0)


def run(cfg: IBSConfig, inst: InstrumentSpec, exchange: str, chart_tf: int,
        date_from: str | None = None, date_to: str | None = None):
    htf_minutes = int(cfg.zoneDetectionTF)
    htf_ms = htf_minutes * 60_000

    chart = _load(exchange, f"{chart_tf}m")
    htf_df = _load(exchange, f"{htf_minutes}m")

    # Orezanie na rovnake okno, ake videl TradingView. Oreze sa aj VSTUP, nie len
    # vypis - inak by engine poznal zony z historie, ktoru TV vobec nemal nacitanu,
    # obchodoval by z nich a porovnanie by nesedelo.
    import pandas as _pd

    if date_from:
        start = _pd.Timestamp(date_from, tz="UTC")
        chart = chart[chart["date"] >= start]
        htf_df = htf_df[htf_df["date"] >= start]
    if date_to:
        end = _pd.Timestamp(date_to, tz="UTC") + _pd.Timedelta(days=1)
        chart = chart[chart["date"] < end]
        htf_df = htf_df[htf_df["date"] < end]

    # 1m detail na rozhodnutie "SL alebo TP skor" - rovnaky princip ako
    # freqtrade --timeframe-detail 1m.
    detail_by_bar: dict[int, list[Bar]] = {}
    try:
        detail_df = _load(exchange, "1m")
    except SystemExit:
        detail_df = None
        print("  ! 1m data chybaju - fill sa rozhoduje na 3m baroch (hrubsie)", file=sys.stderr)
    if detail_df is not None:
        step = chart_tf * 60_000
        for r in detail_df.itertuples(index=False):
            detail_by_bar.setdefault(int(r.ts) // step * step, []).append(_to_bar(r))
    htf_df["vol_sma"] = htf_df["volume"].rolling(cfg.volSmaLen).mean()

    htf_bars = {int(r.ts): _to_bar(r) for r in htf_df.itertuples(index=False)}
    htf_sma = {
        int(r.ts): (float(r.vol_sma) if r.vol_sma == r.vol_sma else 0.0)
        for r in htf_df.itertuples(index=False)
    }

    clock = SessionClock(cfg)
    book = ZoneBook(cfg, inst, chart_tf)
    machine = StateMachine(cfg, inst, book)
    history = BarHistory(
        maxlen=max(cfg.imbLookback, cfg.slLookback, cfg.volSmaLen) + 50, atr_len=cfg.atrLen
    )
    sim = FillSimulator()

    prev_htf_open: int | None = None
    transitions = 0
    reasons: dict[str, int] = {}

    for row in chart.itertuples(index=False):
        bar = _to_bar(row)
        history.append(bar)
        sim.step(bar, detail_by_bar.get(bar.time))

        state = clock.state(bar.time)

        htf_open = bar.time // htf_ms * htf_ms
        if prev_htf_open is not None and htf_open != prev_htf_open and state.in_zone_window:
            opens = htf_window_opens(bar.time, chart_tf * 60_000, htf_ms)
            if all(o in htf_bars for o in opens):
                win = HTFWindow(tuple(htf_bars[o] for o in opens), htf_sma[opens[0]])
                pattern = detect_sd_pattern(win, cfg, inst, atr=history.atr)
                if pattern is not None:
                    zone = book.create_from_pattern(pattern, now_ms=bar.time)
                    if zone is not None:
                        zone.created_bar_index = history.bar_index
        prev_htf_open = htf_open

        ctx = MarketContext(
            in_trade_window=state.in_trade_window,
            position_size=sim.position_size,
            # Pine `dailyWinLimitReached` - po maxDailyWins vyhrach za den sa uz
            # v ten den neposiela ziadny novy order.
            daily_win_limit_reached=sim.wins_today(bar.time) >= cfg.maxDailyWins,
            open_order_ids=sim.open_ids,
        )
        intents = machine.on_bar(bar, history, ctx, atr=history.atr)
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
    ap.add_argument("--from", dest="date_from", help="YYYY-MM-DD, vratane")
    ap.add_argument("--to", dest="date_to", help="YYYY-MM-DD, vratane")
    args = ap.parse_args(argv)

    cfg, inst = load_profile(args.profile)
    book, sim, transitions, reasons = run(cfg, inst, args.exchange, args.chart_tf, args.date_from, args.date_to)

    def fmt(ms: int | None) -> str:
        if ms is None:
            return "-"
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%m-%d %H:%M")

    trades = list(sim.trades.values())
    if args.date_from:
        from datetime import datetime as _dt
        start_ms = int(_dt.fromisoformat(args.date_from).replace(tzinfo=timezone.utc).timestamp() * 1000)
        trades = [t for t in trades if t.placed_ms >= start_ms]

    counts: dict[str, int] = {}
    for t in trades:
        counts[t.outcome] = counts.get(t.outcome, 0) + 1

    print(f"\nProfil {args.profile} na {args.exchange}, graf {args.chart_tf}m")
    print(f"  zon v evidencii:  {len(book)}")
    print(f"  prechodov stavov: {transitions}")
    print(f"  orderov:          {len(trades)}")
    if sim.ambiguous_bars:
        print(f"  nerozhodnutelnych barov (SL aj TP naraz): {sim.ambiguous_bars}")
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

    by_day: dict[str, list[str]] = {}
    for tr in trades:
        if tr.outcome in ("WIN", "LOSS"):
            by_day.setdefault(fmt(tr.placed_ms)[:5], []).append(tr.outcome[0])
    if by_day:
        print("\n  Po dnoch (na porovnanie s TradingView dashboardom):")
        for day, outcomes in sorted(by_day.items()):
            w = outcomes.count("W")
            print(f"    {day}  {''.join(outcomes):<8} {w}W / {len(outcomes) - w}L")

    if sim.trades:
        print(f"\n  {'order':<10} {'zadany':<12} {'vyplneny':<12} {'entry':>10} {'SL':>10} {'TP':>10} {'qty':>8}  stav")
        for t in (trades[-args.limit:] if args.limit else trades):
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
