"""Engine Fibo: impulz → návrat k Fibonacciho úrovniam → vstup na potvrdzovaciu sviečku.

Priebeh:

  1. **swingy** na `swingTF` (skladá sa z barov grafu): pivot so `swingLen` barmi z oboch strán,
     použije sa až po potvrdení.
  2. **noha** vznikne potvrdením swingu: rastúca = od posledného swing dna po tento swing vrchol
     (klesajúca zrkadlovo), aspoň `legMinAtr` ATR dlhá; pri `requireBreak` musí vrchol prekonať
     predošlý swing vrchol (jasný trend). Fibonacci: 0 % = koniec nohy, 100 % = jej začiatok.
  3. **návrat**: sleduje sa extrém návratu od konca nohy. Setup padá, keď cena prerazí 100 %
     (už to nie je návrat), keď prekoná koniec nohy bez vstupu (noha pokračuje — príde nová),
     alebo po `setupMaxBars`.
  4. **vstup**: hĺbka návratu je medzi najplytšou a najhlbšou zapnutou úrovňou (`zone`), alebo
     pri niektorej z nich (`levels`), a na grafe príde vstupný model v smere nohy — IBS
     imbalance alebo pin bar — najviac `signalMaxBars` barov po sviečke s extrémom návratu.
  5. **stop** za začiatok nohy (`leg`) alebo za extrém návratu (`pullback`), **cieľ** extenzia
     nohy (`tpExtensionPct`, −27 %) alebo RR.

Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle, LineStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..jss.engine import StructAggregator
from .config import EntryModel, FiboConfig, LevelMode, SlMode, TpMode
from .drawing import FIB_ENTRY, FIB_LEG, FIB_LEVEL

__all__ = ["FiboEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_FIB_COLOR = "#eab308"
_LEG_COLOR = "#94a3b8"


@dataclass
class _Pivot:
    price: float
    idx: int     #: index baru TF swingov
    time: int


@dataclass
class _Setup:
    """Noha a návrat k nej. `start` je 100 %, `end` je 0 %."""

    uid: int
    direction: Direction
    start: float
    end: float
    start_ms: int
    end_ms: int
    born: int            #: index baru TF swingov, na ktorom sa noha potvrdila
    extreme: float       #: extrém návratu (long: najnižší low od konca nohy)
    extreme_idx: int     #: index baru grafu, ktorý extrém spravil (pri extréme spred potvrdenia nohy bar potvrdenia)

    @property
    def size(self) -> float:
        return abs(self.end - self.start)

    def level(self, frac: float) -> float:
        """Cena úrovne návratu `frac` (0 = koniec nohy, 1 = začiatok); záporné = extenzia."""
        return self.end - frac * (self.end - self.start)

    @property
    def depth(self) -> float:
        """Hĺbka návratu ako podiel nohy."""
        return abs(self.end - self.extreme) / self.size if self.size > 0 else 0.0


class FiboEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: FiboConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        tf = int(cfg.swingTF)
        if tf < self.chart_tf_minutes or tf % self.chart_tf_minutes:
            tf = -(-max(tf, self.chart_tf_minutes) // self.chart_tf_minutes) * self.chart_tf_minutes
        self.swing_tf = tf
        self.agg = StructAggregator(tf, self.chart_tf_minutes)
        n = int(cfg.swingLen)
        self.sbars: deque[Bar] = deque(maxlen=2 * n + 4)
        self.s_idx = -1
        self.s_atr = 0.0
        self._s_seed: list[float] = []
        self.ph: _Pivot | None = None        #: posledný potvrdený swing vrchol
        self.pl: _Pivot | None = None
        self.prev_ph: _Pivot | None = None   #: ten pred ním (pre `requireBreak`)
        self.prev_pl: _Pivot | None = None

        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen}", int(cfg.atrLen) + 8)
        self.warmup.add_seeded(f"swingy {tf}m", 2 * n + int(cfg.atrLen) + 60, tf, self._seed)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=max(self.required_history, 8) + 16, atr_len=int(cfg.atrLen))

        self.setups: dict[Direction, _Setup] = {}
        self._uid = 0
        self._seeding = False
        self._zone = ZoneInfo(cfg.tradeTZ)
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._entry_idx = -1

    # ------------------------------------------------------------------ #
    # swingy a nohy
    # ------------------------------------------------------------------ #

    def _seed(self, bars, partial: Bar | None) -> None:
        self._seeding = True
        for b in bars:
            self._on_swing_bar(b, None)
        self._seeding = False
        self.agg.prime(partial)

    def _on_swing_bar(self, b: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        prev = self.sbars[-1] if self.sbars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
        if self.s_atr > 0:
            self.s_atr += (tr - self.s_atr) / int(cfg.atrLen)
        else:
            self._s_seed.append(tr)
            if len(self._s_seed) >= int(cfg.atrLen):
                self.s_atr = sum(self._s_seed) / len(self._s_seed)
        self.sbars.append(b)
        self.s_idx += 1
        n = int(cfg.swingLen)
        if len(self.sbars) < 2 * n + 1:
            return
        c = self.sbars[-n - 1]
        side = [self.sbars[-n - 1 - k] for k in range(1, n + 1)] + [self.sbars[-k] for k in range(1, n + 1)]
        right = [self.sbars[-k] for k in range(1, n + 1)]
        ci = self.s_idx - n
        if all(c.high > x.high for x in side):
            self.prev_ph, self.ph = self.ph, _Pivot(c.high, ci, c.time)
            self._leg(Direction.LONG, right, out)
        if all(c.low < x.low for x in side):
            self.prev_pl, self.pl = self.pl, _Pivot(c.low, ci, c.time)
            self._leg(Direction.SHORT, right, out)

    def _leg(self, d: Direction, right: list[Bar], out: EngineOutput | None) -> None:
        """Práve potvrdený swing je koniec nohy; jej začiatok je posledný opačný swing pred ním."""
        cfg = self.cfg
        up = d is Direction.LONG
        end, start, prev_end = (self.ph, self.pl, self.prev_ph) if up else (self.pl, self.ph, self.prev_pl)
        if self._seeding or end is None or start is None or start.idx >= end.idx or self.s_atr <= 0:
            return
        size = end.price - start.price if up else start.price - end.price
        if size <= 0 or size < cfg.legMinAtr.value * self.s_atr:
            return
        if cfg.legMaxBars > 0 and end.idx - start.idx > cfg.legMaxBars:
            return
        if cfg.requireBreak and (prev_end is None or (end.price <= prev_end.price if up else end.price >= prev_end.price)):
            return
        # návrat od konca nohy po potvrdenie swingu (bary vpravo od pivotu)
        ext = min(x.low for x in right) if up else max(x.high for x in right)
        if (ext <= start.price) if up else (ext >= start.price):
            return   # už pred potvrdením prerazil 100 % — nie je to návrat
        old = self.setups.get(d)
        if old is not None and out is not None:
            self._draw(out, old, end.time)
        self._uid += 1
        # extrém spred potvrdenia nohy sa ráta ako „práve teraz" — signál môže prísť hneď po potvrdení
        self.setups[d] = _Setup(self._uid, d, start.price, end.price, start.time, end.time, self.s_idx, ext,
                                self.history.bar_index)

    # ------------------------------------------------------------------ #
    # kresby
    # ------------------------------------------------------------------ #

    def _draw(self, out: EngineOutput, s: _Setup, end_ms: int, traded: bool = False) -> None:
        if not self.cfg.showFibo or not traded:
            return   # kreslia sa len nohy, na ktorých vznikol obchod
        end_ms = max(end_ms, s.end_ms)
        out.drawings.append(DrawLine(FIB_LEG, s.start_ms, s.start, s.end_ms, s.end, _LEG_COLOR, style=LineStyle.DASHED,
                                     obj_id=f"fib.leg.{s.uid}", text="noha"))
        fracs = [0.0, *self.cfg.levels(), 1.0]
        if self.cfg.tpMode is TpMode.EXTENSION:
            fracs.append(-self.cfg.tpExtensionPct / 100.0)
        for f in fracs:
            y = s.level(f)
            out.drawings.append(DrawLine(FIB_LEVEL, s.end_ms, y, end_ms, y, _FIB_COLOR,
                                         obj_id=f"fib.lv.{s.uid}.{f:g}", text=f"{f * 100:g} %"))

    # ------------------------------------------------------------------ #
    # vstupné modely (graf)
    # ------------------------------------------------------------------ #

    def _imbalance(self, long: bool, atr: float) -> bool:
        if not self.history.has(3):
            return False
        b0, b1, b2 = self.history[0], self.history[1], self.history[2]
        m = self.cfg.imbMinSizeAtr.value * atr
        if long:
            return b0.low > b2.high and b1.close > b2.high and (b0.low - b2.high) >= m
        return b0.high < b2.low and b1.close < b2.low and (b2.low - b0.high) >= m

    def _pinbar(self, bar: Bar, long: bool) -> bool:
        rng = bar.high - bar.low
        if rng <= 0 or abs(bar.close - bar.open) > self.cfg.pbBodyPct / 100.0 * rng:
            return False
        wick = (min(bar.open, bar.close) - bar.low) if long else (bar.high - max(bar.open, bar.close))
        return wick >= self.cfg.pbWickPct / 100.0 * rng

    def _signal(self, bar: Bar, long: bool, atr: float) -> bool:
        m = self.cfg.entryModel
        if m is EntryModel.IMBALANCE:
            return self._imbalance(long, atr)
        if m is EntryModel.PINBAR:
            return self._pinbar(bar, long)
        return self._imbalance(long, atr) or self._pinbar(bar, long)

    def _at_level(self, s: _Setup, atr: float) -> bool:
        """Je dno návratu tam, kde sa má obchodovať?"""
        cfg = self.cfg
        lv = cfg.levels()
        tol = cfg.levelTolAtr.value * atr / s.size if s.size > 0 else 0.0
        d = s.depth
        if cfg.levelMode is LevelMode.ZONE:
            return lv[0] - tol <= d <= lv[-1] + tol
        return any(abs(d - x) <= tol for x in lv)

    def _plan(self, s: _Setup, entry: float, atr: float) -> TradePlan | None:
        cfg = self.cfg
        long = s.direction is Direction.LONG
        buf = (cfg.slBufferAtr.resolve(self.inst, price=entry, atr=atr)
               + cfg.slBufferPoints.resolve(self.inst, price=entry, atr=atr))
        base = s.start if cfg.slMode is SlMode.LEG else s.extreme
        stop = base - buf if long else base + buf
        sl = entry - stop if long else stop - entry
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl < min_sl:
            return None
        if cfg.tpMode is TpMode.RR:
            take = entry + sl * cfg.rrRatio if long else entry - sl * cfg.rrRatio
        else:
            take = s.level(-cfg.tpExtensionPct / 100.0)
            if (take - entry if long else entry - take) < sl * cfg.minRR:
                return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=s.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

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

        if cfg.maxHoldBars > 0 and ctx.position_size != 0.0 and self._entry_idx >= 0 \
                and idx - self._entry_idx >= cfg.maxHoldBars:
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx,
                                              reason=f"drží sa dlhšie než {cfg.maxHoldBars} barov"))
            self._entry_idx = -1

        free = ctx.position_size == 0.0 and atr > 0
        for d in list(self.setups):
            s = self.setups[d]
            long = d is Direction.LONG
            # zneplatnenie: 100 % prerazené, noha pokračuje, alebo setup vypršal
            if (bar.low < s.start if long else bar.high > s.start) \
                    or (bar.high > s.end if long else bar.low < s.end) \
                    or self.s_idx - s.born > cfg.setupMaxBars:
                del self.setups[d]
                continue
            if (bar.low < s.extreme) if long else (bar.high > s.extreme):
                s.extreme, s.extreme_idx = (bar.low if long else bar.high), idx
            if not free or (long and not cfg.allow_long) or (not long and not cfg.allow_short):
                continue
            if s.extreme_idx < 0 or (cfg.signalMaxBars > 0 and idx - s.extreme_idx > cfg.signalMaxBars):
                continue
            if not self._at_level(s, atr) or not self._signal(bar, long, atr):
                continue
            if not self._in_window(bar) or self._trades_today >= cfg.maxTradesPerDay:
                continue
            plan = self._plan(s, bar.close, atr)
            if plan is None:
                continue
            out.orders.append(OrderIntent(OrderAction.ENTRY, f"fib:{idx}", idx, direction=d, plan=plan,
                                          order_type=OrderType.MARKET,
                                          reason=f"návrat {s.depth * 100:.0f} % + {cfg.entryModel.value}"))
            out.drawings.append(DrawLabel(
                FIB_ENTRY, bar.time, bar.low if long else bar.high, f"{'LONG' if long else 'SHORT'} {s.depth * 100:.0f} %",
                "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"fib.e.{bar.time}"))
            self._draw(out, s, bar.time, traded=True)
            self._trades_today += 1
            self._entry_idx = idx
            del self.setups[d]
            free = False

        for sb in self.agg.push(bar):
            self._on_swing_bar(sb, out)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
