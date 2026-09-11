"""Engine Range Breakout: konsolidácia kdekoľvek na grafe, jej prerazenie a pokračovanie.

Na rozdiel od ORB tu range nie je viazaný na otvorenie seansy — hľadá sa priebežne
v posuvnom okne posledných ``lookbackBars`` barov. Priebeh:

  1. **hľadanie** — okno posledných N barov je range, keď jeho šírka sedí do pásma
     ``minWidthAtr``–``maxWidthAtr`` (v ATR, aby to platilo na každom trhu)
  2. **nabitie** — hranice sa zafixujú; range starne, po ``maxRangeAgeBars`` sa hľadá nanovo
  3. **prerazenie** — close za hranicou + ``breakBufferAtr``; voliteľne sa žiada druhý close
  4. **vstup** podľa ``entryMode``:
     - ``close``        — hneď na zavretí prerazovacej sviečky
     - ``retest``       — limitka na návrat k prerazenej hranici
     - ``continuation`` — po retestte sa ešte čaká na potvrdzujúci close v smere prerazenia
  5. **SL/TP** podľa ``slMode`` / ``tpMode``, veľkosť z rizika
  6. **zlyhané prerazenie** — keď sa cena vráti späť do rangu, setup sa zahodí

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import BoundaryMode, EntryMode, RangeConfig, SlMode, TpMode
from .drawing import RANGE_BOX, RANGE_BREAK, RANGE_ENTRY, RANGE_HIGH, RANGE_LOW

__all__ = ["RangeEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_RANGE_FILL = "#f59e0b28"
_RANGE_LINE = "#f59e0bb3"


@dataclass
class _Range:
    """Nabitý range: zafixované hranice a stav prerazenia."""

    high: float
    low: float
    start_ms: int
    arm_bar: int
    #: smer prerazenia, kým sa čaká na retest/potvrdenie
    break_dir: Direction | None = None
    break_level: float = 0.0
    break_bar: int = -1
    break_extreme: float = 0.0
    #: pri `requireSecondClose` prvý close za hranicou, ktorý ešte nestačí
    pending_dir: Direction | None = None
    #: pri `continuation` — retest sa už udial, čaká sa na potvrdzujúci close
    retested: bool = False
    retest_bar: int = -1

    @property
    def height(self) -> float:
        return self.high - self.low


class RangeEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: RangeConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000

        self.required_history = int(cfg.atrLen) + int(cfg.lookbackBars) + 8
        self.history = BarHistory(maxlen=self.required_history + 16, atr_len=int(cfg.atrLen))

        self._zone = ZoneInfo(cfg.tradeTZ)
        self._rng: _Range | None = None
        self._cooldown_until = -1
        self._pending: tuple[str, int] | None = None
        self._entry_bar: int = -1
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._in_window_prev = False

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _stop_level(self, rng: _Range, direction: Direction, entry: float, atr: float) -> float:
        cfg = self.cfg
        long = direction is Direction.LONG
        hi, lo = rng.high, rng.low
        if cfg.slMode is SlMode.OPPOSITE:
            base = lo if long else hi
        elif cfg.slMode is SlMode.MID:
            base = (hi + lo) / 2.0
        elif cfg.slMode is SlMode.RANGE_PCT:
            depth = rng.height * (cfg.slRangePct / 100.0)
            base = hi - depth if long else lo + depth
        elif cfg.slMode is SlMode.BREAK_CANDLE:
            base = rng.break_extreme
        else:  # ATR
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
            base = entry - dist if long else entry + dist
        buffer = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        return base - buffer if long else base + buffer

    def _target_level(self, rng: _Range, direction: Direction, entry: float,
                      sl_distance: float, atr: float) -> float:
        cfg = self.cfg
        long = direction is Direction.LONG
        if cfg.tpMode is TpMode.RR:
            dist = sl_distance * cfg.rrRatio
        elif cfg.tpMode is TpMode.MEASURED:
            dist = rng.height * cfg.measuredMult
        else:  # ATR
            dist = cfg.tpAtrMult.resolve(self.inst, price=entry, atr=atr)
        return entry + dist if long else entry - dist

    def _plan(self, rng: _Range, direction: Direction, entry: float, atr: float) -> TradePlan | None:
        stop = self._stop_level(rng, direction, entry, atr)
        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        take = self._target_level(rng, direction, entry, sl_distance, atr)
        if (direction is Direction.LONG and take <= entry) or (
            direction is Direction.SHORT and take >= entry
        ):
            return None

        qty = (self.inst.qty_for_risk(self.cfg.riskDollar, sl_distance)
               if self.cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)

        trailing = None
        if self.cfg.enableTrailing:
            act = sl_distance * self.cfg.trailActivationR
            off = sl_distance * self.cfg.trailOffsetR
            tick = self.inst.tick_size or 1.0
            trailing = TrailingPlan(
                activation_price_distance=act, offset_price_distance=off,
                activation_ticks=act / tick, offset_ticks=off / tick,
            )
        return TradePlan(
            direction=direction, entry=self.inst.round_price(entry),
            stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
            qty=qty, sl_distance=sl_distance, trailing=trailing,
        )

    # ------------------------------------------------------------------ #
    # detekcia rangu
    # ------------------------------------------------------------------ #

    def _detect(self, idx: int, atr: float, bar: Bar) -> _Range | None:
        """Je okno posledných `lookbackBars` barov dosť tesné na range?"""
        cfg = self.cfg
        n = int(cfg.lookbackBars)
        if not self.history.has(n) or atr <= 0:
            return None
        bars = [self.history[i] for i in range(n)]
        if cfg.boundaryMode is BoundaryMode.CLOSE:
            hi = max(b.close for b in bars)
            lo = min(b.close for b in bars)
        else:
            hi = max(b.high for b in bars)
            lo = min(b.low for b in bars)
        width = hi - lo
        lo_lim = cfg.minWidthAtr.resolve(self.inst, price=bar.close, atr=atr)
        hi_lim = cfg.maxWidthAtr.resolve(self.inst, price=bar.close, atr=atr)
        if not (lo_lim <= width <= hi_lim) or width <= 0:
            return None
        return _Range(high=hi, low=lo, start_ms=bars[-1].time, arm_bar=idx)

    def _close_position_ok(self, bar: Bar, long: bool) -> bool:
        span = bar.high - bar.low
        if span <= 0:
            return True
        pos = (bar.close - bar.low) / span * 100.0
        return pos >= self.cfg.minClosePosPct if long else (100.0 - pos) >= self.cfg.minClosePosPct

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        minutes = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= minutes < cfg.window_end_minutes

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day = day
            self._trades_today = 0

        # nevyplnená limitka z predchádzajúceho baru
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None
        elif self._entry_bar >= 0:
            self._entry_bar = -1

        in_window = self._in_window(bar)

        # ---- koniec obchodného okna: zavri, čo je otvorené ---------------- #
        if cfg.closeAtWindowEnd and self._in_window_prev and not in_window and ctx.position_size != 0.0:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason="koniec obchodného okna"))
        self._in_window_prev = in_window

        # ---- maximálna dĺžka obchodu -------------------------------------- #
        if (cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_bar >= 0
                and idx - self._entry_bar >= cfg.maxHoldBars):
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_bar = -1

        if ctx.position_size != 0.0 or self._pending is not None:
            return out
        if idx < self._cooldown_until:
            return out

        # ---- 1./2. hľadanie a nabitie rangu ------------------------------- #
        if self._rng is None:
            self._rng = self._detect(idx, atr, bar)
            if self._rng is not None and cfg.showRange:
                out.drawings.append(DrawBox(
                    RANGE_BOX, self._rng.start_ms, self._rng.high, bar.time, self._rng.low,
                    _RANGE_FILL, obj_id=f"rng.{bar.time}", text="range",
                ))
                if cfg.showLevels:
                    end_ms = bar.time + self.step_ms * int(cfg.maxRangeAgeBars)
                    out.drawings.append(DrawLine(RANGE_HIGH, bar.time, self._rng.high, end_ms,
                                                 self._rng.high, _RANGE_LINE,
                                                 obj_id=f"rngh.{bar.time}", text="range high"))
                    out.drawings.append(DrawLine(RANGE_LOW, bar.time, self._rng.low, end_ms,
                                                 self._rng.low, _RANGE_LINE,
                                                 obj_id=f"rngl.{bar.time}", text="range low"))
            return out

        rng = self._rng

        # ---- range zostarol bez prerazenia -------------------------------- #
        if rng.break_dir is None and idx - rng.arm_bar > cfg.maxRangeAgeBars:
            self._rng = None
            return out

        buffer = cfg.breakBufferAtr.resolve(self.inst, price=bar.close, atr=atr)

        # ---- 3. hľadanie prerazenia --------------------------------------- #
        if rng.break_dir is None:
            long_break = cfg.allow_long and bar.close > rng.high + buffer
            short_break = cfg.allow_short and bar.close < rng.low - buffer
            if not (long_break or short_break):
                rng.pending_dir = None
                return out
            direction = Direction.LONG if long_break else Direction.SHORT

            if not in_window or self._trades_today >= cfg.maxTradesPerDay:
                return out
            if not self._close_position_ok(bar, long_break):
                return out
            if cfg.requireSecondClose and rng.pending_dir is not direction:
                rng.pending_dir = direction     # prvý close za hranicou ešte nestačí
                return out

            rng.break_dir = direction
            rng.break_level = rng.high if long_break else rng.low
            rng.break_bar = idx
            rng.break_extreme = bar.low if long_break else bar.high
            out.drawings.append(DrawLabel(
                RANGE_BREAK, bar.time, bar.high if long_break else bar.low,
                "prerazenie", "#ffffff", style=LabelStyle.NONE, above=long_break,
                bg_color=_LONG_COLOR if long_break else _SHORT_COLOR,
                obj_id=f"rngb.{bar.time}",
            ))
            if cfg.entryMode is EntryMode.CLOSE:
                self._enter(out, rng, direction, bar.close, atr, idx, bar,
                            OrderType.MARKET, "prerazenie rangu")
            return out

        # ---- 4. retest / pokračovanie ------------------------------------- #
        long = rng.break_dir is Direction.LONG

        # zlyhané prerazenie: cena zavrela späť vnútri rangu
        back_inside = bar.close < rng.high if long else bar.close > rng.low
        if back_inside and idx > rng.break_bar:
            self._rng = None
            self._cooldown_until = idx + int(cfg.cooldownBars)
            return out

        if idx - rng.break_bar > cfg.retestMaxBars:
            self._rng = None
            return out
        if not in_window or self._trades_today >= cfg.maxTradesPerDay:
            return out

        if not rng.retested:
            touched = bar.low <= rng.break_level if long else bar.high >= rng.break_level
            if not touched:
                return out
            rng.retested = True
            rng.retest_bar = idx
            if cfg.entryMode is EntryMode.RETEST:
                self._enter(out, rng, rng.break_dir, rng.break_level, atr, idx, bar,
                            OrderType.LIMIT, "retest hranice")
            return out

        # continuation: po retestte ešte potvrdzujúci close v smere prerazenia
        if cfg.entryMode is EntryMode.CONTINUATION:
            if idx - rng.retest_bar > cfg.confirmMaxBars:
                self._rng = None
                return out
            confirmed = bar.close > rng.break_level if long else bar.close < rng.break_level
            if confirmed and self._close_position_ok(bar, long):
                self._enter(out, rng, rng.break_dir, bar.close, atr, idx, bar,
                            OrderType.MARKET, "pokračovanie po retestte")
        return out

    # ------------------------------------------------------------------ #

    def _enter(self, out: EngineOutput, rng: _Range, direction: Direction, entry: float,
               atr: float, idx: int, bar: Bar, order_type: OrderType, reason: str) -> None:
        plan = self._plan(rng, direction, entry, atr)
        if plan is None:
            self._rng = None
            return
        order_id = f"range:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                      plan=plan, order_type=order_type, reason=reason))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        self._trades_today += 1
        long = direction is Direction.LONG
        out.drawings.append(DrawLabel(
            RANGE_ENTRY, bar.time, bar.low if long else bar.high,
            f"{'LONG' if long else 'SHORT'} range", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR,
            obj_id=f"rnge.{bar.time}",
        ))
        self._rng = None
        self._cooldown_until = idx + int(self.cfg.cooldownBars)

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
