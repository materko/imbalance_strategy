"""Engine Silver Bullet 1.0 (ICT): okno 10:00–11:00 NY → výber likvidity → FVG v protismere → limitka.

Priebeh na každom uzavretom bare grafu (minúta = čas **zavretia** baru v New Yorku; `_update` je to isté aj
pre predhistóriu pred behom):

  1. **deň** — nový deň New York vymaže likviditu, sweepy aj setup,
  2. **likvidita** — high / low úseku `liqFrom`–začiatok okna (do okna vstúpi ako hotová úroveň) a swingy grafu
     (`liqPivotLen`) od `liqFrom`; úroveň, ktorú cena prerazí, zmizne — pred oknom bez obchodu, v okne je to sweep,
  3. **sweep** (len v okne) — prerazenie sell-side (dno) → čaká sa na long, buy-side (vrchol) → short; extrém sa
     posúva, kým cena ide ďalej,
  4. **FVG** — medzera medzi 1. a 3. sviečkou v smere obchodu (≥ `fvgMinAtr` ATR), ktorej 1. sviečka nie je
     skôr ako extrém sweepu, do `fvgMaxBars` barov od extrému; pri `requireMss` až po zavretí za posledný swing
     grafu pred extrémom,
  5. **vstup** — limitka na okraji / strede FVG, platí na ďalší bar a obnovuje sa do konca okna (alebo market na
     zavretí sviečky, ktorá FVG vytvorila); setup zruší cena za stopom alebo v cieli pred vyplnením a koniec okna,
  6. **SL** za extrém sweepu + rezerva, **TP** najbližšia nevybratá protiľahlá likvidita aspoň `minRR` R (alebo RR).

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle,
                                   with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from .config import EntryLevel, EntryType, SilverBulletConfig, TpMode
from .drawing import SB_ENTRY, SB_FVG, SB_LIQ_BUY, SB_LIQ_SELL, SB_SWEEP, SB_WINDOW

__all__ = ["SilverBulletEngine"]

NY = ZoneInfo("America/New_York")
LONG_COLOR, SHORT_COLOR = "#10b981", "#ef4444"
BSL_COLOR, SSL_COLOR = "#ef4444d9", "#10b981d9"
FVG_COLOR = "#a855f7"
WINDOW_COLOR = "#a855f7"


@dataclass
class _Level:
    side: str            #: "buy" (vrchol nad cenou) / "sell" (dno pod cenou)
    price: float
    start_ms: int
    label: str
    uid: int


@dataclass
class _Sweep:
    direction: Direction  #: smer obchodu (výber sell-side → long)
    level: float
    extreme: float
    extreme_ms: int
    extreme_idx: int
    mss_level: float | None   #: posledný swing grafu pred extrémom (pre requireMss)
    mss: bool = False


@dataclass
class _Setup:
    direction: Direction
    extreme: float
    top: float
    bottom: float
    t0: int
    idx: int
    box_id: str = ""

    @property
    def long(self) -> bool:
        return self.direction is Direction.LONG


class SilverBulletEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: SilverBulletConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg, self.inst = cfg, inst
        self.tf = max(1, int(chart_tf_minutes))
        self.step_ms = self.tf * 60_000
        self.history = BarHistory(maxlen=int(cfg.atrLen) + 8, atr_len=int(cfg.atrLen))
        self.idx = -1
        self.day: tuple[int, int, int] | None = None
        self.levels: list[_Level] = []
        self._uid = 0
        self.range_hi: float | None = None
        self.range_lo: float | None = None
        self._range_t0: int | None = None
        self._range_added = False
        n = max(int(cfg.liqPivotLen), int(cfg.structPivotLen))
        self._win: deque[Bar] = deque(maxlen=2 * n + 1)
        self.struct_hi: deque[tuple[int, float]] = deque(maxlen=200)
        self.struct_lo: deque[tuple[int, float]] = deque(maxlen=200)
        self.sweeps: dict[Direction, _Sweep] = {}
        self.setup: _Setup | None = None
        self._pending: tuple[str, int, TradePlan, _Setup] | None = None
        self._trades_today = 0
        self._boxes: list[str] = []
        self._was_in = False
        self._window_box: str | None = None
        # predhistória: deň likvidity pred oknom + ATR
        bars = 1440 // self.tf + 2 * int(cfg.atrLen) + 4 * n
        self.warmup = Warmup(self.tf).add_seeded("likvidita dňa a ATR", bars, self.tf, self._seed)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #

    def _seed(self, closed: list[Bar], partial: Bar | None) -> None:
        for bar in closed:
            self._update(bar, None)

    def _minute(self, bar: Bar) -> tuple[tuple[int, int, int], int, int]:
        t = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=NY)
        return (t.year, t.month, t.day), t.hour * 60 + t.minute, t.weekday()

    def _add(self, side: str, price: float, start_ms: int, label: str) -> None:
        self._uid += 1
        self.levels.append(_Level(side, price, start_ms, label, self._uid))

    def _draw_level(self, lv: _Level, end_ms: int) -> DrawLine:
        buy = lv.side == "buy"
        return DrawLine(SB_LIQ_BUY if buy else SB_LIQ_SELL, lv.start_ms, lv.price, end_ms, lv.price,
                        BSL_COLOR if buy else SSL_COLOR, obj_id=f"sb.liq.{lv.side}.{lv.start_ms}.{lv.uid}",
                        text=lv.label)

    def _new_day(self, day, out: EngineOutput | None) -> None:
        if out is not None and self.cfg.showLevels:
            # nevybraté úrovne predošlého dňa končia na jeho konci
            end = self.history[0].time + self.step_ms if self.history.has(1) else 0
            out.drawings += [self._draw_level(lv, end) for lv in self.levels]
        self.day = day
        self.levels = []
        self.range_hi = self.range_lo = None
        self._range_t0 = None
        self._range_added = False
        self.sweeps = {}
        self.setup = None
        self._trades_today = 0
        self._window_box = None
        self.struct_hi.clear()
        self.struct_lo.clear()

    def _update(self, bar: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        self.idx += 1
        idx = self.idx
        draw = out is not None
        day, m, _wd = self._minute(bar)
        if day != self.day:
            self._new_day(day, out)
        self.history.append(bar)
        atr = self.history.atr
        start, end = cfg.window
        in_window = start < m <= end

        # ---- úsek pred oknom: high / low --------------------------------------- #
        if cfg.liq_from < m <= start:
            if self._range_t0 is None:
                self._range_t0 = bar.time
            self.range_hi = bar.high if self.range_hi is None else max(self.range_hi, bar.high)
            self.range_lo = bar.low if self.range_lo is None else min(self.range_lo, bar.low)
        if in_window and not self._range_added:
            self._range_added = True
            if cfg.useRangeHL and self.range_hi is not None:
                self._add("buy", self.range_hi, self._range_t0, "high pred oknom")
                self._add("sell", self.range_lo, self._range_t0, "low pred oknom")
            if draw and cfg.showWindow:
                self._window_box = f"sb.win.{bar.time}"
                out.drawings.append(DrawBox(SB_WINDOW, bar.time, bar.high, bar.time + self.step_ms, bar.low,
                                            WINDOW_COLOR, fill_color=with_alpha(WINDOW_COLOR, 25),
                                            obj_id=self._window_box, text="Silver Bullet"))

        # ---- výber likvidity (v okne sweep, pred ním úroveň len zmizne) --------- #
        keep: list[_Level] = []
        for lv in self.levels:
            buy = lv.side == "buy"
            if not ((buy and bar.high > lv.price) or (not buy and bar.low < lv.price)):
                keep.append(lv)
                continue
            if draw and cfg.showLevels:
                out.drawings.append(self._draw_level(lv, bar.time))
            if not in_window:
                continue
            if cfg.sweepReclaim and ((buy and bar.close >= lv.price) or (not buy and bar.close <= lv.price)):
                continue
            d = Direction.SHORT if buy else Direction.LONG
            if (d is Direction.LONG and not cfg.allow_long) or (d is Direction.SHORT and not cfg.allow_short):
                continue
            ext = bar.high if buy else bar.low
            old = self.sweeps.get(d)
            if old is not None and ((buy and old.extreme >= ext) or (not buy and old.extreme <= ext)):
                continue
            swings = self.struct_lo if buy else self.struct_hi
            prior = [s for s in swings if s[0] < bar.time]
            self.sweeps[d] = _Sweep(d, lv.price, ext, bar.time, idx, prior[-1][1] if prior else None)
            if draw and cfg.showLevels:
                out.drawings.append(DrawLabel(SB_SWEEP, bar.time, ext, "sweep", "#ffffff",
                                              style=LabelStyle.DOWN if buy else LabelStyle.UP, above=buy,
                                              bg_color=SHORT_COLOR if buy else LONG_COLOR,
                                              obj_id=f"sb.sw.{bar.time}.{lv.side}"))
        self.levels = keep

        # ---- swingy grafu: likvidita od liqFrom + štruktúra pre MSS -------------- #
        self._win.append(bar)
        for n, as_liq in ((int(cfg.liqPivotLen), True), (int(cfg.structPivotLen), False)):
            if len(self._win) < 2 * n + 1:
                continue
            w = list(self._win)[-(2 * n + 1):]
            c, left, right = w[n], w[:n], w[n + 1:]
            hi = all(c.high > x.high for x in left) and all(c.high >= x.high for x in right)
            lo = all(c.low < x.low for x in left) and all(c.low <= x.low for x in right)
            c_day, c_m, _ = self._minute(c)
            today = c_day == self.day
            if as_liq:
                if cfg.useSwings and today and c_m > cfg.liq_from and m <= end:
                    if hi and not any(bar_.high > c.high for bar_ in right):
                        self._add("buy", c.high, c.time, "skorší vrchol")
                    if lo and not any(bar_.low < c.low for bar_ in right):
                        self._add("sell", c.low, c.time, "skoršie dno")
            else:
                if hi:
                    self.struct_hi.append((c.time, c.high))
                if lo:
                    self.struct_lo.append((c.time, c.low))

        # ---- sweep: extrém sa posúva, MSS, FVG ---------------------------------- #
        if not in_window:
            self.sweeps = {}
        for d in list(self.sweeps):
            s = self.sweeps[d]
            long = d is Direction.LONG
            if s.extreme_idx < idx:
                if long and bar.low < s.extreme:
                    s.extreme, s.extreme_ms, s.extreme_idx = bar.low, bar.time, idx
                elif not long and bar.high > s.extreme:
                    s.extreme, s.extreme_ms, s.extreme_idx = bar.high, bar.time, idx
            if s.mss_level is not None and ((long and bar.close > s.mss_level) or (not long and bar.close < s.mss_level)):
                s.mss = True
            if idx - s.extreme_idx > int(cfg.fvgMaxBars):
                del self.sweeps[d]
                continue
            if not self.history.has(3) or atr <= 0 or self.setup is not None:
                continue
            if cfg.requireMss and not s.mss:
                continue
            b0, b2 = self.history[0], self.history[2]
            min_gap = cfg.fvgMinAtr.resolve(self.inst, price=bar.close, atr=atr)
            if b2.time < s.extreme_ms:
                continue
            if long and b0.low > b2.high and b0.low - b2.high >= min_gap:
                self.setup = _Setup(d, s.extreme, b0.low, b2.high, b2.time, idx)
            elif not long and b0.high < b2.low and b2.low - b0.high >= min_gap:
                self.setup = _Setup(d, s.extreme, b2.low, b0.high, b2.time, idx)
            if self.setup is not None:
                del self.sweeps[d]
                if draw and cfg.showFvg:
                    st = self.setup
                    st.box_id = f"sb.fvg.{st.t0}"
                    out.drawings.append(DrawBox(SB_FVG, st.t0, st.top, bar.time + self.step_ms, st.bottom, FVG_COLOR,
                                                fill_color=with_alpha(FVG_COLOR, 50), obj_id=st.box_id, text="FVG"))

        # ---- setup: zneplatnenie ------------------------------------------------- #
        st = self.setup
        if st is None:
            return
        if not in_window or (st.long and bar.low <= st.extreme) or (not st.long and bar.high >= st.extreme):
            self.setup = None                       # koniec okna alebo cena za extrémom pred vyplnením
            return
        if idx > st.idx:
            plan = self._plan(st, self._entry_price(st))
            if plan is None or (st.long and bar.high >= plan.take_profit) or (not st.long and bar.low <= plan.take_profit):
                self.setup = None                   # cieľ dosiahnutý bez nás / nie je kam

    # ------------------------------------------------------------------ #

    def _entry_price(self, st: _Setup) -> float:
        if self.cfg.entryLevel is EntryLevel.MID:
            return (st.top + st.bottom) / 2.0
        return st.top if st.long else st.bottom

    def _plan(self, st: _Setup, entry: float) -> TradePlan | None:
        cfg = self.cfg
        atr = self.history.atr
        buf = cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        stop = st.extreme - buf if st.long else st.extreme + buf
        sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2 or (st.long and stop >= entry) or (not st.long and stop <= entry):
            return None
        max_sl = cfg.maxSlAtr.resolve(self.inst, price=entry, atr=atr) if atr > 0 else 0.0
        if max_sl > 0 and sl > max_sl:
            return None
        if cfg.tpMode is TpMode.LIQUIDITY:
            side = "buy" if st.long else "sell"
            beyond = cfg.minRR * sl
            levels = [lv.price for lv in self.levels if lv.side == side
                      and ((lv.price > entry + beyond) if st.long else (lv.price < entry - beyond))]
            if not levels:
                return None
            dist = (min(levels) - entry) if st.long else (entry - max(levels))
        else:
            dist = cfg.rrRatio * sl
        if dist <= 0:
            return None
        take = entry + dist if st.long else entry - dist
        qty = cfg.qty if cfg.fixedQty else self.inst.qty_for_risk(cfg.riskDollar, sl)
        return TradePlan(direction=st.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty if qty > 0 else 1.0, sl_distance=sl)

    def _draw_trade(self, out: EngineOutput, t: int, plan: TradePlan) -> None:
        long = plan.direction is Direction.LONG
        self._boxes = []
        for kind, level, color in ((DrawKind.TP_BOX, plan.take_profit, LONG_COLOR),
                                   (DrawKind.SL_BOX, plan.stop_loss, SHORT_COLOR)):
            oid = f"sb.{'tp' if kind == DrawKind.TP_BOX else 'sl'}.{t}"
            out.drawings.append(DrawBox(kind, t, max(plan.entry, level), t + self.step_ms, min(plan.entry, level),
                                        color, fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self._boxes.append(oid)
        out.drawings.append(DrawLabel(SB_ENTRY, t, plan.entry, f"{'LONG' if long else 'SHORT'} Silver Bullet",
                                      "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"sb.e.{t}"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        cfg, out = self.cfg, EngineOutput()
        pos = ctx.position_size
        if self._boxes:                              # boxy bežiaceho obchodu rastú doprava
            for oid in self._boxes:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if pos != 0.0:
                self._was_in = True
            elif self._was_in:
                self._boxes, self._was_in = [], False
        if self._pending is not None:                # limitka z minulého baru: vyplnená, alebo zrušiť
            oid, pidx, plan, pst = self._pending
            if pos != 0.0 or oid in ctx.open_order_ids:
                self._trades_today += 1
                self._draw_trade(out, bar.time, plan)
                self._was_in = pos != 0.0
                if not self._was_in:
                    self._boxes = []
                if self.setup is pst:
                    self.setup = None
            else:
                out.orders.append(OrderIntent(OrderAction.CANCEL, oid, pidx, reason="nevyplnené"))
            self._pending = None

        self._update(bar, out)
        idx = self.idx
        day, m, wd = self._minute(bar)
        if self._window_box and cfg.window[0] < m <= cfg.window[1]:
            out.drawings.append(DrawUpdate(self._window_box, "x2_ms", bar.time + self.step_ms))
        st = self.setup
        if st is not None and st.box_id:
            out.drawings.append(DrawUpdate(st.box_id, "x2_ms", bar.time + self.step_ms))

        if cfg.useExitTime and pos != 0.0 and m >= cfg.exit_minutes and m - cfg.exit_minutes < self.tf:
            out.close_session = True
            for oid in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason="výstup v čase"))
            return out
        if pos != 0.0 or st is None or self._trades_today >= int(cfg.maxTradesPerDay):
            return out
        if cfg.weekdaysOnly and wd >= 5:
            return out

        if cfg.entryType is EntryType.MARKET:
            if st.idx != idx:
                return out
            plan = self._plan(st, bar.close)
            self.setup = None
            if plan is None:
                return out
            self._trades_today += 1
            self._draw_trade(out, bar.time, plan)          # box od baru signálu (páruje sa s obchodom)
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"sb:{bar.time}", idx, direction=st.direction, plan=plan,
                                          order_type=OrderType.MARKET, reason="Silver Bullet: sweep + FVG"))
            return out

        entry = self._entry_price(st)
        if (st.long and bar.close <= entry) or (not st.long and bar.close >= entry):
            return out
        plan = self._plan(st, entry)
        if plan is None:
            return out
        oid = f"sb:{bar.time}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=st.direction, plan=plan,
                                      order_type=OrderType.LIMIT, reason="Silver Bullet: sweep + FVG"))
        self._pending = (oid, idx, plan, st)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        """Nevybratá likvidita na konci dát — po posledný bar."""
        if not self.cfg.showLevels:
            return []
        end = bar.time + self.step_ms
        return [self._draw_level(lv, end) for lv in self.levels]
