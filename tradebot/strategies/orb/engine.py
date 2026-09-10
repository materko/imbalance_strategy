"""Engine ORB: každá zapnutá seansa si postaví vlastný opening range a obchoduje jeho prerazenie.

Priebeh jednej seansy v jeden deň:

  1. bary od otvorenia seansy po ``rangeMinutes`` stavajú **opening range** (high/low)
  2. keď okno rangu skončí, range sa uzavrie a skontrolujú sa filtre šírky
  3. v obchodnom okne sa čaká na **prerazenie** hranice (close za ňou + buffer)
  4. podľa ``entryMode`` sa vstúpi hneď, alebo sa čaká na retest hranice
  5. SL a TP sa počítajú podľa ``slMode`` / ``tpMode``
  6. na konci seansy sa pozícia zatvorí (``closeAtSessionEnd``)

Seansy sú nezávislé: New York a Londýn majú vlastný range, vlastný denný limit obchodov
aj vlastný koniec. Prekrývajú sa (NY 9:30 = Londýn 14:30), takže sa spracúvajú v poradí
a nová pozícia sa neotvorí, kým je iná otvorená — o to sa stará ``ctx.position_size``.

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import EntryMode, ORBConfig, SessionWindow, SlMode, TpMode
from .drawing import ORB_BOX, ORB_ENTRY, ORB_HIGH, ORB_LOW

__all__ = ["ORBEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
#: Každá seansa má vlastnú farbu, nech sa na grafe nepomýlia.
_RANGE_COLORS = {"ny": "#3b82f628", "london": "#a855f728"}
_LEVEL_COLORS = {"ny": "#3b82f6b3", "london": "#a855f7b3"}


@dataclass
class _SessionState:
    """Stav jednej seansy v jeden deň."""

    day: tuple[int, int, int] | None = None
    high: float | None = None
    low: float | None = None
    open_ms: int = 0
    closed: bool = False
    ok: bool = False
    trades: int = 0
    break_dir: Direction | None = None
    break_level: float = 0.0
    break_bar: int = -1
    break_extreme: float = 0.0

    def reset(self, day: tuple[int, int, int], ts_ms: int) -> None:
        self.day = day
        self.high = None
        self.low = None
        self.open_ms = ts_ms
        self.closed = False
        self.ok = False
        self.trades = 0
        self.break_dir = None
        self.break_bar = -1


class ORBEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: ORBConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000

        self.sessions: tuple[SessionWindow, ...] = cfg.sessions
        self._zones = {s.key: ZoneInfo(s.tz) for s in self.sessions}
        self._state: dict[str, _SessionState] = {s.key: _SessionState() for s in self.sessions}
        #: v ktorej seanse vznikla otvorená pozícia — jej koniec ju aj zatvorí
        self._open_session: str | None = None

        self.required_history = int(cfg.atrLen) + int(cfg.volSmaLen) + 16
        self.history = BarHistory(maxlen=self.required_history + 16, atr_len=int(cfg.atrLen))
        self._pending: tuple[str, int] | None = None

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _stop_level(self, st: _SessionState, direction: Direction, entry: float,
                    atr: float) -> float | None:
        cfg = self.cfg
        long = direction is Direction.LONG
        hi, lo = st.high, st.low
        if hi is None or lo is None:
            return None
        if cfg.slMode is SlMode.OPPOSITE:
            base = lo if long else hi
        elif cfg.slMode is SlMode.MID:
            base = (hi + lo) / 2.0
        elif cfg.slMode is SlMode.RANGE_PCT:
            # od prerazenej hranice smerom do rangu; 100 % = opačná hrana
            depth = (hi - lo) * (cfg.slRangePct / 100.0)
            base = hi - depth if long else lo + depth
        elif cfg.slMode is SlMode.BREAK_CANDLE:
            base = st.break_extreme
        else:  # ATR
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
            base = entry - dist if long else entry + dist
        buffer = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        return base - buffer if long else base + buffer

    def _target_level(self, st: _SessionState, direction: Direction, entry: float,
                      sl_distance: float, atr: float) -> float:
        cfg = self.cfg
        long = direction is Direction.LONG
        hi, lo = st.high or entry, st.low or entry
        if cfg.tpMode is TpMode.RR:
            dist = sl_distance * cfg.rrRatio
        elif cfg.tpMode is TpMode.MEASURED:
            dist = (hi - lo) * cfg.measuredMult
        else:  # ATR
            dist = cfg.tpAtrMult.resolve(self.inst, price=entry, atr=atr)
        return entry + dist if long else entry - dist

    def _plan(self, st: _SessionState, direction: Direction, entry: float,
              atr: float) -> TradePlan | None:
        stop = self._stop_level(st, direction, entry, atr)
        if stop is None:
            return None
        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        take = self._target_level(st, direction, entry, sl_distance, atr)
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
    # filtre
    # ------------------------------------------------------------------ #

    def _range_passes(self, st: _SessionState, price: float) -> bool:
        if st.high is None or st.low is None or price <= 0:
            return False
        width_pct = (st.high - st.low) / price * 100.0
        return self.cfg.minRangePct <= width_pct <= self.cfg.maxRangePct

    def _volume_ok(self, bar: Bar) -> bool:
        if not self.cfg.useVolumeFilter:
            return True
        n = int(self.cfg.volSmaLen)
        if not self.history.has(n):
            return False
        avg = sum(self.history[i].volume for i in range(1, n + 1)) / n
        return avg > 0 and bar.volume >= avg * self.cfg.volMultiplier

    def _close_position_ok(self, bar: Bar, long: bool) -> bool:
        span = bar.high - bar.low
        if span <= 0:
            return True
        pos = (bar.close - bar.low) / span * 100.0
        return pos >= self.cfg.minClosePosPct if long else (100.0 - pos) >= self.cfg.minClosePosPct

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        # zrušenie nevyplnenej limitky z predchádzajúceho baru
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None
        if ctx.position_size == 0.0:
            self._open_session = None

        for sess in self.sessions:
            self._on_session(out, sess, bar, atr, idx, ctx)
        return out

    # ------------------------------------------------------------------ #

    def _on_session(self, out: EngineOutput, sess: SessionWindow, bar: Bar, atr: float,
                    idx: int, ctx: MarketContext) -> None:
        cfg = self.cfg
        st = self._state[sess.key]
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zones[sess.key])
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return
        minutes = local.hour * 60 + local.minute

        day = (local.year, local.month, local.day)
        if day != st.day:
            st.reset(day, bar.time)

        # ---- 1. stavanie rangu ------------------------------------------ #
        if sess.start_minutes <= minutes < sess.range_end_minutes:
            st.high = bar.high if st.high is None else max(st.high, bar.high)
            st.low = bar.low if st.low is None else min(st.low, bar.low)
            st.open_ms = min(st.open_ms or bar.time, bar.time)
            return

        # ---- 2. range práve uzavretý ------------------------------------ #
        if not st.closed and minutes >= sess.range_end_minutes and st.high is not None and st.low is not None:
            st.closed = True
            st.ok = self._range_passes(st, bar.close)
            if cfg.showRange:
                out.drawings.append(DrawBox(
                    ORB_BOX, st.open_ms, st.high, bar.time, st.low,
                    _RANGE_COLORS.get(sess.key, "#3b82f628"),
                    obj_id=f"orb.{sess.key}.{day}", text=f"{sess.title} range",
                ))
            if cfg.showLevels:
                end_ms = bar.time + self.step_ms * 120
                color = _LEVEL_COLORS.get(sess.key, "#3b82f6b3")
                out.drawings.append(DrawLine(ORB_HIGH, bar.time, st.high, end_ms, st.high, color,
                                             obj_id=f"orbh.{sess.key}.{day}",
                                             text=f"{sess.title} high"))
                out.drawings.append(DrawLine(ORB_LOW, bar.time, st.low, end_ms, st.low, color,
                                             obj_id=f"orbl.{sess.key}.{day}",
                                             text=f"{sess.title} low"))

        # ---- 6. koniec seansy — zatvára len tá, v ktorej pozícia vznikla -- #
        if minutes >= sess.end_minutes:
            if (cfg.closeAtSessionEnd and ctx.position_size != 0.0
                    and self._open_session == sess.key):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                                  reason=f"koniec seansy {sess.title}"))
                self._open_session = None
            st.break_dir = None
            return

        # ---- mantinely obchodného okna ----------------------------------- #
        if not (st.closed and st.ok) or minutes < sess.range_end_minutes:
            return
        if cfg.entryWindowMinutes > 0 and minutes > sess.start_minutes + cfg.entryWindowMinutes:
            return
        if st.trades >= cfg.maxTradesPerDay:
            return
        if ctx.position_size != 0.0 or self._pending is not None:
            return

        hi, lo = st.high, st.low
        buffer = cfg.breakBufferAtr.resolve(self.inst, price=bar.close, atr=atr)

        # ---- 3. hľadanie prerazenia -------------------------------------- #
        if st.break_dir is None:
            long_break = cfg.allow_long and bar.close > hi + buffer
            short_break = cfg.allow_short and bar.close < lo - buffer
            if not (long_break or short_break):
                return
            if not self._volume_ok(bar) or not self._close_position_ok(bar, long_break):
                return
            st.break_dir = Direction.LONG if long_break else Direction.SHORT
            st.break_level = hi if long_break else lo
            st.break_bar = idx
            st.break_extreme = bar.low if long_break else bar.high

            if cfg.entryMode is EntryMode.RETEST:
                return  # čaká sa na návrat k hranici
            entry = bar.close if cfg.entryMode is EntryMode.CLOSE else st.break_level
            order_type = OrderType.MARKET if cfg.entryMode is EntryMode.CLOSE else OrderType.STOP
            self._enter(out, sess, st, st.break_dir, entry, atr, idx, bar, order_type,
                        f"prerazenie {sess.title}")
            return

        # ---- 4. retest --------------------------------------------------- #
        if cfg.entryMode is EntryMode.RETEST:
            if idx - st.break_bar > cfg.retestMaxBars:
                st.break_dir = None
                return
            long = st.break_dir is Direction.LONG
            touched = bar.low <= st.break_level if long else bar.high >= st.break_level
            if touched:
                self._enter(out, sess, st, st.break_dir, st.break_level, atr, idx, bar,
                            OrderType.LIMIT, f"retest hranice {sess.title}")

    # ------------------------------------------------------------------ #

    def _enter(self, out: EngineOutput, sess: SessionWindow, st: _SessionState,
               direction: Direction, entry: float, atr: float, idx: int, bar: Bar,
               order_type: OrderType, reason: str) -> None:
        plan = self._plan(st, direction, entry, atr)
        if plan is None:
            st.break_dir = None
            return
        order_id = f"orb:{sess.key}:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction,
                                      plan=plan, order_type=order_type, reason=reason))
        self._pending = (order_id, idx)
        self._open_session = sess.key
        st.trades += 1
        st.break_dir = None
        long = direction is Direction.LONG
        out.drawings.append(DrawLabel(
            ORB_ENTRY, bar.time, bar.low if long else bar.high,
            f"{'LONG' if long else 'SHORT'} {sess.title}", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR,
            obj_id=f"orb_entry.{sess.key}.{bar.time}",
        ))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
