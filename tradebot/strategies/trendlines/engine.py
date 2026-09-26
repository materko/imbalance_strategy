"""Engine Trendline Breakout: trendovka cez pivoty na vlastnom TF a jej prerazenie na grafe.

Priebeh:

  1. **trendovky** — na `lineTF` (5m až 4h, skladá sa z barov grafu) sa z pivotov kreslí
     odpor a podpora (`lines.py`); obchodovateľná je až s `minTouches` dotykmi
  2. **prerazenie** — zavretie baru grafu za čiarou + `breakBufferAtr`, s polohou zavretia
     aspoň `minClosePosPct`; každá čiara sa prerazí (a obchoduje) najviac raz
  3. **vstup** podľa `entryMode`:
     - ``close``        — hneď na zavretí prerazovacej sviečky
     - ``second_close`` — až druhé zavretie za čiarou za sebou
     - ``retest``       — limitka na prerazenú čiaru (jej hodnota sa s časom posúva)
     - ``retest_close`` — dotyk čiary a zavretie späť v smere prerazenia
  4. **SL** podľa `slMode`, **TP** = `rrRatio` × vzdialenosť SL, veľkosť z rizika
  5. **zlyhané prerazenie** — zavretie späť za čiarou setup zahodí

Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..divergence.htf import TFAggregator
from .config import EntryMode, SlMode, TrendlineConfig
from .drawing import TL_BREAK, TL_ENTRY, TL_PIVOT, TL_RESISTANCE, TL_SUPPORT
from .lines import Line, LineBook

__all__ = ["TrendlineEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_RES_COLOR = "#ef4444cc"
_SUP_COLOR = "#10b981cc"


@dataclass
class _Setup:
    """Prerazená čiara, kým sa čaká na druhé zavretie alebo retest."""

    line: Line
    direction: Direction
    break_bar: int
    break_extreme: float
    retested: bool = False
    #: pri `retest` už bola položená limitka — do denného limitu sa setup počíta raz
    ordered: bool = False


class TrendlineEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: TrendlineConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        line_tf = cfg.line_tf_minutes
        if line_tf < self.chart_tf_minutes or line_tf % self.chart_tf_minutes != 0:
            raise ValueError(
                f"TF trendoviek {line_tf}m musí byť násobkom TF grafu {self.chart_tf_minutes}m "
                "(a nie menší) — skladá sa z barov grafu")
        self.agg = TFAggregator(line_tf)
        self.lines = LineBook(cfg, line_tf * 60_000)

        #: predhistória grafu: ATR a okno SL; trendovky majú vlastnú na svojom TF (seed)
        self.warmup = Warmup(self.chart_tf_minutes).add(
            f"ATR {cfg.atrLen} + SL okno {cfg.slLookback}", int(cfg.atrLen) + int(cfg.slLookback) + 8)
        self.warmup.add_seeded(
            f"trendovky {line_tf}m", int(cfg.lineMaxAgeBars) + 2 * int(cfg.pivotLen) + int(cfg.atrLen) + 5,
            line_tf, self._seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, int(cfg.slLookback) + 4) + 16,
                                  atr_len=int(cfg.atrLen))

        self._zone = ZoneInfo(cfg.tradeTZ)
        self._setup: _Setup | None = None
        self._pending: tuple[str, int] | None = None
        self._entry_bar = -1
        self._cooldown_until = -1
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._in_window_prev = False
        self.breaks = 0

    # ------------------------------------------------------------------ #
    # predhistória trendoviek
    # ------------------------------------------------------------------ #

    def _seed(self, bars, partial: Bar | None) -> None:
        if self.lines.count or self.agg.started:
            raise RuntimeError(f"{self.agg.minutes}m: seeding smie ísť len pred prvým barom grafu")
        for b in bars:
            self.lines.on_htf_bar(b)
        self.agg.prime(partial)

    # ------------------------------------------------------------------ #
    # plán obchodu
    # ------------------------------------------------------------------ #

    def _plan(self, setup: _Setup, entry: float, t_ms: int, atr: float) -> TradePlan | None:
        cfg = self.cfg
        direction = setup.direction
        long = direction is Direction.LONG
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
        if cfg.slMode is SlMode.LINE:
            base = setup.line.value(t_ms)
        elif cfg.slMode is SlMode.BREAK_CANDLE:
            base = setup.break_extreme
        elif cfg.slMode is SlMode.SWING:
            n = min(int(cfg.slLookback), len(self.history))
            recent = [self.history[i] for i in range(n)]
            base = min(b.low for b in recent) if long else max(b.high for b in recent)
        else:  # ATR
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
            base = entry - dist if long else entry + dist
        stop = base - buf if long else base + buf
        sl_distance = entry - stop if long else stop - entry
        if sl_distance < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None
        take = entry + sl_distance * cfg.rrRatio if long else entry - sl_distance * cfg.rrRatio
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        trailing = None
        if cfg.enableTrailing:
            act = sl_distance * cfg.trailActivationR
            off = sl_distance * cfg.trailOffsetR
            tick = self.inst.tick_size or 1.0
            trailing = TrailingPlan(activation_price_distance=act, offset_price_distance=off,
                                    activation_ticks=act / tick, offset_ticks=off / tick)
        return TradePlan(direction=direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl_distance, trailing=trailing)

    # ------------------------------------------------------------------ #

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        minutes = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= minutes < cfg.window_end_minutes

    def _close_position_ok(self, bar: Bar, long: bool) -> bool:
        span = bar.high - bar.low
        if span <= 0:
            return True
        pos = (bar.close - bar.low) / span * 100.0
        return pos >= self.cfg.minClosePosPct if long else (100.0 - pos) >= self.cfg.minClosePosPct

    def _draw_lines(self, out: EngineOutput) -> None:
        cfg = self.cfg
        if cfg.showPivots:
            for kind, p in self.lines.new_pivots:
                high = kind == "res"
                out.drawings.append(DrawLabel(
                    TL_PIVOT, p.t, p.price, "▼" if high else "▲",
                    _SHORT_COLOR if high else _LONG_COLOR, style=LabelStyle.NONE, above=high,
                    obj_id=f"tlp.{kind}.{p.t}"))
        if not cfg.showLines:
            return
        tf_ms = self.lines.tf_ms
        for ln in self.lines.new_lines:
            end = ln.t2 + tf_ms * int(cfg.lineMaxAgeBars)
            res = ln.kind == "res"
            out.drawings.append(DrawLine(
                TL_RESISTANCE if res else TL_SUPPORT, ln.t1, ln.y1, end, ln.value(end),
                _RES_COLOR if res else _SUP_COLOR, obj_id=f"tl.{ln.kind}.{ln.t1}.{ln.t2}",
                text=f"{'odpor' if res else 'podpora'} {cfg.lineTF}m ({ln.touches}x)"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        # vyšší TF: uzavretý bar predchádzajúcej periódy ide do trendoviek PRED rozhodovaním
        closed = self.agg.push(bar)
        if closed is not None:
            self.lines.on_htf_bar(closed)
            self._draw_lines(out)

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        t_close = bar.time + self.step_ms

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
        elif self._entry_bar >= 0 and self._pending is None:
            self._entry_bar = -1

        in_window = self._in_window(bar)
        if cfg.closeAtWindowEnd and self._in_window_prev and not in_window and ctx.position_size != 0.0:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason="koniec obchodného okna"))
        self._in_window_prev = in_window

        if (cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_bar >= 0
                and idx - self._entry_bar >= cfg.maxHoldBars):
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_bar = -1

        if ctx.position_size != 0.0:
            self._setup = None          # limitka z retestu sa vyplnila — setup je minulosť
            return out
        if atr <= 0:
            return out

        buffer = cfg.breakBufferAtr.resolve(self.inst, price=bar.close, atr=atr)
        tol = cfg.touchTolAtr.value * atr

        # ---- rozpracovaný setup (druhé zavretie / retest) ---------------- #
        if self._setup is not None:
            self._continue_setup(out, bar, idx, atr, buffer, tol, t_close, in_window)
            return out
        if self._pending is not None or idx < self._cooldown_until:
            return out

        # ---- prerazenie ---------------------------------------------------- #
        for name, direction in (("res", Direction.LONG), ("sup", Direction.SHORT)):
            ln: Line | None = getattr(self.lines, name)
            if ln is None or ln.consumed or ln.touches < cfg.minTouches:
                continue
            v = ln.value(t_close)
            long = direction is Direction.LONG
            crossed = bar.close > v + buffer if long else bar.close < v - buffer
            if not crossed:
                continue
            ln.consumed = True          # každá čiara sa prerazí najviac raz
            self.breaks += 1
            allowed = cfg.allow_long if long else cfg.allow_short
            if (not allowed or not in_window or self._trades_today >= cfg.maxTradesPerDay
                    or not self._close_position_ok(bar, long)):
                continue
            out.drawings.append(DrawLabel(
                TL_BREAK, bar.time, bar.high if long else bar.low, "prerazenie", "#ffffff",
                style=LabelStyle.NONE, above=long, bg_color=_LONG_COLOR if long else _SHORT_COLOR,
                obj_id=f"tlb.{bar.time}"))
            setup = _Setup(ln, direction, idx, bar.low if long else bar.high)
            if cfg.entryMode is EntryMode.CLOSE:
                self._enter(out, setup, bar.close, t_close, atr, idx, bar, OrderType.MARKET,
                            "prerazenie trendovky")
            else:
                self._setup = setup
                if cfg.entryMode is EntryMode.RETEST:
                    self._place_retest(out, setup, idx, atr, bar)
            break
        return out

    def _continue_setup(self, out: EngineOutput, bar: Bar, idx: int, atr: float, buffer: float,
                        tol: float, t_close: int, in_window: bool) -> None:
        cfg = self.cfg
        s = self._setup
        long = s.direction is Direction.LONG
        v = s.line.value(t_close)
        # zlyhané prerazenie: zavretie späť za čiaru
        failed = bar.close < v - buffer if long else bar.close > v + buffer
        if failed or idx - s.break_bar > cfg.retestMaxBars or not in_window \
                or self._trades_today >= cfg.maxTradesPerDay:
            self._setup = None
            self._cooldown_until = idx + int(cfg.cooldownBars)
            return
        beyond = bar.close > v + buffer if long else bar.close < v - buffer

        if cfg.entryMode is EntryMode.SECOND_CLOSE:
            if beyond and self._close_position_ok(bar, long):
                self._enter(out, s, bar.close, t_close, atr, idx, bar, OrderType.MARKET,
                            "druhé zavretie za trendovkou")
            else:
                self._setup = None
                self._cooldown_until = idx + int(cfg.cooldownBars)
            return

        if cfg.entryMode is EntryMode.RETEST:
            if self._pending is None:     # limitka z minulého baru sa zrušila -> nová na posunutej čiare
                self._place_retest(out, s, idx, atr, bar)
            return

        # RETEST_CLOSE: najprv dotyk čiary, potom zavretie späť v smere prerazenia
        touched = bar.low <= v + tol if long else bar.high >= v - tol
        if touched:
            s.retested = True
        if s.retested and beyond and self._close_position_ok(bar, long) and idx > s.break_bar:
            self._enter(out, s, bar.close, t_close, atr, idx, bar, OrderType.MARKET,
                        "retest trendovky a zavretie")

    def _place_retest(self, out: EngineOutput, s: _Setup, idx: int, atr: float, bar: Bar) -> None:
        """Limitka na hodnotu čiary na konci nasledujúceho baru (čiara sa posúva)."""
        level = s.line.value(bar.time + 2 * self.step_ms)
        long = s.direction is Direction.LONG
        if (long and level >= bar.close) or (not long and level <= bar.close):
            return
        plan = self._plan(s, level, bar.time + 2 * self.step_ms, atr)
        if plan is None:
            self._setup = None
            return
        order_id = f"tl:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=s.direction,
                                      plan=plan, order_type=OrderType.LIMIT, reason="retest trendovky"))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        if not s.ordered:
            s.ordered = True
            self._trades_today += 1

    def _enter(self, out: EngineOutput, s: _Setup, entry: float, t_ms: int, atr: float, idx: int,
               bar: Bar, order_type: OrderType, reason: str) -> None:
        self._setup = None
        self._cooldown_until = idx + int(self.cfg.cooldownBars)
        plan = self._plan(s, entry, t_ms, atr)
        if plan is None:
            return
        order_id = f"tl:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=s.direction,
                                      plan=plan, order_type=order_type, reason=reason))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        self._trades_today += 1
        long = s.direction is Direction.LONG
        out.drawings.append(DrawLabel(
            TL_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} TL",
            "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"tle.{bar.time}"))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
