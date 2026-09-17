"""Emulátor backtestu MultiCharts nad 1m dátami — ten istý `MCRunner`, ale bez MultiCharts.

Webapp „burza" **MultiCharts** (Dukascopy dáta v `data/`) nejde cez
Freqtrade: Dukascopy nie je burza v ccxt a Freqtrade by pár odmietol. Beh sa preto počíta
tu, cez presne tú istú cestu ako študia v MultiCharts (`MCRunner` -> engine stratégie),
a broker MultiCharts sa emuluje podľa toho, ako sa naozaj správa:

* order zadaný na close baru platí na **ďalší bar**; market sa vyplní na jeho otvorení,
  limitka pri dotyku ceny (alebo na otvorení, ak je cena už za limitom);
* naraz je **jedna pozícia**; ďalší vstup sa neplní, kým beží;
* SL a TP platia od vyplnenia (adaptér ich posiela spolu so vstupom) a rozhodujú sa po
  **1m sviečkach**, teda ako Freqtrade `--timeframe-detail 1m` a ako MultiCharts s
  Bar Magnifier 1m; SL aj TP v tej istej minúte = nerozhodnuteľné, berie sa SL a počíta sa;
* koniec seansy zavrie pozíciu na **close aktuálneho baru** (`MarketThisBar`);
* trailing stop prepočíta runner na close každého baru (ako v študii).

Predhistória grafu sa neemuluje (engine začína na `from_ms`, ako doteraz). Indikátory
s vlastnou predhistóriou na svojom TF (IBS Supertrend/ADX, vyššie TF divergencie) sa však
pred prvým barom seedujú z 1m dát **pred** `from_ms` (`tradebot.core.warmup.seed_engine`) —
rovnako ako vo Freqtrade adaptéri, takže oba enginy majú na prvom bare ten istý stav.

Poplatok je percento z nominálu na stranu (nominál = cena × množstvo × hodnota bodu),
`wallet` je len základ pre percentá — sizing robí stratégia (`maxLossDollar`, prípadne
`legacyPineSizing`). Výsledok má rovnaký tvar ako Freqtrade beh (`result_from_zip`),
takže história webapp vie oba druhy behov ukázať vedľa seba.
"""

from __future__ import annotations

import gzip
import json
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ...core import Bar, DrawRegistry, InstrumentSpec
from ...core.config import StrategyConfig
from ...core.drawing import objects_to_dicts
from ...core.money import summary_money, trade_money
from ...core.types import Direction
from ...core.candles import resample_ohlcv, timeframe_minutes
from ...core.warmup import seed_engine
from .runner import LiveOrder, MCRunner

__all__ = ["EmuTrade", "EmulationResult", "emulate", "bars_from_frame", "rows_from_trades", "summarize",
           "equity_series", "write_chart"]

MIN_MS = 60_000


@dataclass
class EmuTrade:
    order_id: str
    direction: Direction
    qty: float
    entry: float
    open_ms: int
    stop_initial: float
    take_profit: float
    market: bool
    stop_last: float = 0.0
    exit: float | None = None
    close_ms: int | None = None
    reason: str = ""
    max_price: float = 0.0
    min_price: float = 0.0

    @property
    def is_long(self) -> bool:
        return self.direction is Direction.LONG

    @property
    def sign(self) -> float:
        return 1.0 if self.is_long else -1.0

    @property
    def points(self) -> float:
        return (self.exit - self.entry) * self.sign if self.exit is not None else 0.0


@dataclass
class EmulationResult:
    trades: list[EmuTrade]
    bars: int
    first_ms: int | None
    last_ms: int | None
    first_close: float | None
    last_close: float | None
    ambiguous: int
    chart_header: dict[str, Any] | None = None
    daily_closes: list[tuple[int, float]] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# dáta
# --------------------------------------------------------------------------- #


def bars_from_frame(m1, minutes: int, from_ms: int | None = None, to_ms: int | None = None) -> list[Bar]:
    """1m DataFrame (`date`, OHLCV) → uzavreté bary `minutes` zarovnané na epochu."""
    import pandas as pd

    df = m1
    if from_ms is not None:
        df = df[df["date"] >= pd.Timestamp(from_ms, unit="ms", tz="UTC")]
    if to_ms is not None:
        df = df[df["date"] < pd.Timestamp(to_ms, unit="ms", tz="UTC")]
    df = resample_ohlcv(df, minutes)
    ts = (df["date"].astype("datetime64[ns, UTC]").astype("int64") // 1_000_000).to_numpy()
    o, h, l, c, v = (df[k].astype(float).to_numpy() for k in ("open", "high", "low", "close", "volume"))
    return [Bar(time=int(ts[i]), open=float(o[i]), high=float(h[i]), low=float(l[i]), close=float(c[i]), volume=float(v[i]))
            for i in range(len(ts))]


def _seed_before(runner: MCRunner, m1, first_ms: int, log: Callable[[str], None]) -> None:
    """Indikátory s vlastnou predhistóriou z 1m dát pred prvým barom grafu (bez pohľadu dopredu)."""
    warmup = getattr(runner.engine, "warmup", None)
    if warmup is None or not warmup.seeds:
        return
    import pandas as pd

    lo = pd.Timestamp(first_ms - warmup.seed_span_ms, unit="ms", tz="UTC")
    hi = pd.Timestamp(first_ms, unit="ms", tz="UTC")
    before = m1[(m1["date"] >= lo) & (m1["date"] < hi)]
    got = seed_engine(runner.engine, before, first_ms)
    parts = [f"{n.name} @{n.tf_minutes}m {got.get(n.name, 0)}/{n.bars}" for n in warmup.seeds]
    log("predhistoria indikatorov z dat pred behom: " + ", ".join(parts))


# --------------------------------------------------------------------------- #
# broker
# --------------------------------------------------------------------------- #


def _entry_fill(sub: Bar, live: LiveOrder, first_minute: bool) -> float | None:
    """Cena vyplnenia vstupu v 1m sviečke, alebo None."""
    price = float(live.plan.entry)
    if live.market:
        return sub.open if first_minute else None
    if live.is_long:
        if sub.open <= price:
            return sub.open
        return price if sub.low <= price else None
    if sub.open >= price:
        return sub.open
    return price if sub.high >= price else None


def _net_pnl(trade: EmuTrade, inst: InstrumentSpec, fee: float) -> float:
    """Zisk uzavretého obchodu po poplatku — to isté číslo ako `profit_abs` v `rows_from_trades`."""
    if trade.exit is None:
        return 0.0
    return trade_money(trade.entry, trade.exit, trade.qty, is_short=not trade.is_long,
                       point_value=inst.point_value, fee_open=fee).net


def _exit_fill(sub: Bar, trade: EmuTrade, stop: float, tp: float) -> tuple[float, str, bool] | None:
    """(cena, dôvod, nerozhodnuteľné) alebo None. Pri SL aj TP v jednej minúte berie SL."""
    if trade.is_long:
        hit_sl = sub.low <= stop
        hit_tp = sub.high >= tp
        sl_px = min(stop, sub.open) if hit_sl else None
        tp_px = max(tp, sub.open) if hit_tp else None
    else:
        hit_sl = sub.high >= stop
        hit_tp = sub.low <= tp
        sl_px = max(stop, sub.open) if hit_sl else None
        tp_px = min(tp, sub.open) if hit_tp else None
    if not (hit_sl or hit_tp):
        return None
    if hit_sl:
        reason = "trailing_stop" if stop != trade.stop_initial else "stop_loss"
        return float(sl_px), reason, bool(hit_tp)
    return float(tp_px), "take_profit", False


def emulate(
    cfg: StrategyConfig,
    inst: InstrumentSpec,
    m1,
    chart_tf: int,
    *,
    from_ms: int | None = None,
    to_ms: int | None = None,
    log: Callable[[str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    registry: DrawRegistry | None = None,
    spec=None,
    fee: float = 0.0,
) -> tuple[EmulationResult, MCRunner]:
    """Prehrá stratégiu cez `MCRunner` s emulovaným brokerom MultiCharts.

    `m1` je 1m DataFrame (`date` UTC, OHLCV). Vracia výsledok a runner (kvôli kresbám).
    `fee` je poplatok na stranu ako v `rows_from_trades`; tu slúži len na zisk uzavretého
    obchodu pre denný limit výhier (Pine `strategy.closedtrades.profit` je po poplatku).
    """
    out_log = log or (lambda _s: None)
    chart = bars_from_frame(m1, chart_tf, from_ms, to_ms)
    detail = bars_from_frame(m1, 1, from_ms, to_ms)
    step = chart_tf * MIN_MS
    by_bar: dict[int, list[Bar]] = {}
    for b in detail:
        by_bar.setdefault(b.time // step * step, []).append(b)

    runner = MCRunner(cfg, inst, chart_tf, spec=spec)
    if chart:
        _seed_before(runner, m1, chart[0].time, out_log)
    htf_bars: list[Bar] = []
    htf_closes: list[int] = []
    htf_pos = 0
    if runner.htf is not None and runner.spec.informative_tfs:
        htf_minutes = timeframe_minutes(runner.spec.informative_tfs(cfg)[0])
        htf_bars = bars_from_frame(m1, htf_minutes, from_ms, to_ms)
        htf_closes = [b.time + htf_minutes * MIN_MS for b in htf_bars]
    registry = registry if registry is not None else DrawRegistry()

    trades: list[EmuTrade] = []
    open_trade: EmuTrade | None = None
    active_stop = active_tp = 0.0
    pending_entries: list[LiveOrder] = []
    #: koľko uzavretých obchodov už runner dostal (`closed_trade_pnls` = len nové)
    reported = 0
    ambiguous = 0
    first_close = last_close = None
    daily: dict[int, float] = {}
    out_log(f"emulacia MultiCharts: {len(chart)} barov {chart_tf}m, {len(detail)} 1m, {len(htf_bars)} HTF")

    for i, bar in enumerate(chart):
        if should_stop is not None and should_stop():
            out_log("zrusene")
            break
        subs = by_bar.get(bar.time) or [bar]

        # -- broker: vyplnenie orderov zadaných na predchádzajúcom bare -------------
        for k, sub in enumerate(subs):
            filled_now = False
            if open_trade is None and pending_entries:
                for live in pending_entries:
                    px = _entry_fill(sub, live, first_minute=(k == 0))
                    if px is None:
                        continue
                    open_trade = EmuTrade(
                        order_id=live.order_id, direction=live.direction, qty=float(live.plan.qty),
                        entry=px, open_ms=sub.time, stop_initial=float(live.plan.stop_loss),
                        take_profit=float(live.plan.take_profit), market=live.market,
                        stop_last=float(live.plan.stop_loss), max_price=px, min_price=px,
                    )
                    active_stop, active_tp = float(live.plan.stop_loss), float(live.plan.take_profit)
                    filled_now = px == sub.open  # limitka uprostred minúty: výstup až od ďalšej
                    pending_entries = []
                    break
            if open_trade is None:
                continue
            open_trade.max_price = max(open_trade.max_price, sub.high)
            open_trade.min_price = min(open_trade.min_price, sub.low)
            if open_trade.open_ms == sub.time and not filled_now:
                continue
            hit = _exit_fill(sub, open_trade, active_stop, active_tp)
            if hit is None:
                continue
            px, reason, amb = hit
            ambiguous += int(amb)
            open_trade.exit, open_trade.close_ms, open_trade.reason = px, sub.time, reason
            open_trade.stop_last = active_stop
            trades.append(open_trade)
            open_trade = None

        # -- stratégia na close baru ---------------------------------------------
        # HTF bary uzavreté najneskôr v čase uzavretia tohto baru idú do feedera PRED
        # `on_bar` — tak ako v študii (`signal._feed_htf` pred `runner.on_bar`). Pine
        # offset [1] stráži feeder (`htf_window_opens`), nie poradie kŕmenia: pri grafe
        # väčšom než detekčný TF (10m/5m) okno potrebuje bar, ktorý sa uzavrel práve
        # počas tohto baru, a kŕmenie až po `on_bar` dávalo 0 okien.
        if htf_bars:
            end = bisect_right(htf_closes, bar.time + step)
            for hb in htf_bars[htf_pos:end]:
                runner.feed_htf(hb)
            htf_pos = max(htf_pos, end)
        position = open_trade.qty * open_trade.sign if open_trade is not None else 0.0
        out = runner.on_bar(bar, position_size=position, closed_trades=len(trades),
                            closed_trade_pnls=[_net_pnl(t, inst, fee) for t in trades[reported:]])
        reported = len(trades)
        registry.extend(out.drawings)

        if out.close_session and open_trade is not None:
            open_trade.exit, open_trade.close_ms, open_trade.reason = bar.close, bar.time, "session_end"
            open_trade.stop_last = active_stop
            trades.append(open_trade)
            open_trade = None
        if open_trade is not None and out.exit_plan is not None:
            active_stop = float(out.exit_stop if out.exit_stop is not None else out.exit_plan.stop_loss)
            active_tp = float(out.exit_plan.take_profit)
        pending_entries = list(out.entries) if open_trade is None else []

        if first_close is None:
            first_close = bar.close
        last_close = bar.close
        daily[bar.time // 86_400_000] = bar.close
        if i and i % 20000 == 0:
            out_log(f"  {i}/{len(chart)} barov, {len(trades)} obchodov")

    if open_trade is not None:  # koniec dát s otvorenou pozíciou -> zavrieť na poslednom close
        open_trade.exit, open_trade.close_ms, open_trade.reason = last_close, chart[-1].time, "force_exit"
        open_trade.stop_last = active_stop
        trades.append(open_trade)

    out_log(f"hotovo: {len(trades)} obchodov, nerozhodnutelnych minut {ambiguous}")
    result = EmulationResult(
        trades=trades, bars=len(chart), first_ms=chart[0].time if chart else None,
        last_ms=chart[-1].time if chart else None, first_close=first_close, last_close=last_close,
        ambiguous=ambiguous, daily_closes=[(d * 86_400_000, c) for d, c in sorted(daily.items())],
    )
    return result, runner


# --------------------------------------------------------------------------- #
# výsledok v tvare Freqtrade behu
# --------------------------------------------------------------------------- #


def _iso(ms: int | None) -> str | None:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat() if ms is not None else None


def rows_from_trades(trades: list[EmuTrade], inst: InstrumentSpec, fee: float, leverage: float = 1.0) -> list[dict[str, Any]]:
    """Riadky ako `trades.json` z Freqtrade behu — históriu webapp číta jeden formát."""
    rows = []
    lev = max(float(leverage or 1.0), 1.0)
    for t in trades:
        if t.exit is None or t.close_ms is None:
            continue
        # peniaze obchodu: jedna definícia pre oba enginy (tradebot.core.money)
        m = trade_money(t.entry, t.exit, t.qty, is_short=not t.is_long,
                        point_value=inst.point_value, fee_open=fee)
        profit = m.net
        stake = m.notional_open / lev
        rows.append({
            "open_date": _iso(t.open_ms), "close_date": _iso(t.close_ms),
            # 10 miest, nie 6: stop mimo mriežky ticku × lot 100 000 by inak stratil doláre
            "open_rate": round(t.entry, 10), "close_rate": round(t.exit, 10),
            "amount": t.qty, "point_value": float(inst.point_value),
            "stake_amount": round(stake, 4), "leverage": lev,
            "profit_abs": round(profit, 4), "profit_ratio": round(profit / stake, 6) if stake else 0.0,
            "exit_reason": t.reason, "enter_tag": t.order_id, "is_short": not t.is_long,
            "fee_open": fee, "fee_close": fee, "funding_fees": 0.0,
            "trade_duration": int((t.close_ms - t.open_ms) / MIN_MS),
            "initial_stop_loss_abs": t.stop_initial, "stop_loss_abs": t.stop_last,
            "initial_take_profit_abs": t.take_profit,
            "max_rate": t.max_price, "min_rate": t.min_price,
            "gross_abs": round(m.gross, 4), "fees_abs": round(m.fees, 4),
            "order_type": "market" if t.market else "limit",
        })
    return rows


def equity_series(rows: list[dict[str, Any]], wallet: float) -> list[list[Any]]:
    """Krivka `[čas, zisk obchodu %, kumulatívne %]` z uložených obchodov (percentá z peňaženky)."""
    out = []
    cum = 0.0
    for r in rows:
        p = float(r.get("profit_abs") or 0.0)
        cum += p
        out.append([r["close_date"], round(p / wallet * 100.0, 4), round(cum / wallet * 100.0, 4)])
    return out


def summarize(rows: list[dict[str, Any]], wallet: float, result: EmulationResult,
              currency: str = "USD") -> tuple[dict[str, Any], dict[str, Any]]:
    """(súhrn, série) s rovnakými kľúčmi ako `webapp.runner.result_from_zip`."""
    money = summary_money(rows, wallet)  # gross, objem, break-even, drawdown: tradebot.core.money
    equity = equity_series(rows, wallet)
    durations = [r["trade_duration"] for r in rows]
    avg_min = sum(durations) / len(durations) if durations else 0.0
    market_change = ((result.last_close / result.first_close - 1.0) * 100.0) if result.first_close and result.last_close else 0.0

    summary = {
        **money, "stake_currency": currency,
        "market_change_pct": round(market_change, 3),
        "backtest_start": _iso(result.first_ms), "backtest_end": _iso(result.last_ms),
        "holding_avg": f"{int(avg_min // 60)}:{int(avg_min % 60):02d}:00" if rows else "",
        "bars": result.bars, "ambiguous_minutes": result.ambiguous,
        "engine": "multicharts-emulator",
    }
    series = {
        "equity": equity,
        "market": [[_iso(ms), round((c / result.first_close - 1.0) * 100.0, 4)] for ms, c in result.daily_closes]
        if result.first_close else [],
    }
    return summary, series


def write_chart(runner: MCRunner, registry: DrawRegistry, result: EmulationResult, pair: str,
                timeframe: str, path: Path | str) -> dict[str, Any]:
    """Kresby behu v tom istom formáte ako `freqtrade.runner.export_chart` (`chart.json.gz`)."""
    objects = list(registry.objects())
    last = result.last_ms
    if last is not None and hasattr(runner.engine, "final_drawings"):
        from ...core import Bar as _Bar

        try:
            objects.extend(runner.engine.final_drawings(_Bar(time=last, open=result.last_close, high=result.last_close,
                                                             low=result.last_close, close=result.last_close, volume=0.0)))
        except Exception:  # noqa: BLE001 - záverečné kresby sú bonus
            pass
    dicts = objects_to_dicts(objects)
    counts: dict[str, int] = {}
    for d in dicts:
        counts[d["k"]] = counts.get(d["k"], 0) + 1
    data = {
        "version": 1, "strategy": runner.spec.key, "pair": pair, "timeframe": timeframe,
        "from_ms": result.first_ms, "to_ms": result.last_ms, "bars": result.bars, "counts": counts, "objects": dicts,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if path.suffix == ".gz":
        with gzip.open(path, "wb", compresslevel=6) as fh:
            fh.write(raw)
    else:
        path.write_bytes(raw)
    return {k: v for k, v in data.items() if k != "objects"}
