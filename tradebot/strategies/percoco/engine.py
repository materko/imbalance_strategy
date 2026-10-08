"""Engine Craig Percoco 1.0: 15m trend a FVG ako body záujmu, 1m CHoCH + FVG, limitka na stred FVG.

Priebeh (na každom uzavretom bare grafu, typicky 1m):

  1. **15m** (skladá sa z barov grafu): swingy so `htfSwingLen` sviečkami z oboch strán; trend = smer
     posledného prierazu (zavretie nad posledný swing high = rast, pod swing low = pokles). Nové FVG
     v smere (bull: low 3. sviečky nad high 1.), aspoň `htfFvgMinAtr` ATR; FVG zaniká, keď 15m sviečka
     zavrie za jeho vzdialenú hranu, alebo po `htfFvgMaxBars`.
  2. **Dotyk bodu záujmu**: sviečka grafu, ktorá zasiahne živé 15m FVG v smere, si zapamätá čas.
  3. **CHoCH na grafe**: swingy so `swingLen`; zavretie nad posledný swing high, keď bol trend grafu
     dole (zrkadlovo pre short), je CHoCH. Pri `useHtfBias` musí súhlasiť s 15m trendom, pri `useHtfPoi`
     musí prísť najviac `poiBars` sviečok po dotyku 15m FVG.
  4. **FVG v pohybe CHoCH**: posledné FVG (aspoň `fvgMinAtr` ATR) medzi low pohybu a sviečkou CHoCH,
     ktorého stred je pod zavretím (long) — limitka na `entryPct` % FVG (50 = stred),
     stop pod low pohybu (+ `slBufferAtr`), cieľ `rrRatio` × riziko.
  5. Setup zaniká: vyplnením, zavretím za stopom, dosiahnutím cieľa bez vyplnenia, novým CHoCH proti,
     koncom okna alebo po `setupMaxBars`. Limitka platí vždy jednu sviečku a posiela sa znova.

Kresba obchodu (štítok, TP / SL boxy) vzniká až pri vyplnení — nevyplnená limitka v grafe nie je.
Engine je čistý: žiadne I/O, žiadny globálny stav.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import (DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, DrawUpdate, LabelStyle,
                                   LineStyle, with_alpha)
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.warmup import Warmup

from ..jss.engine import StructAggregator
from .config import PercocoConfig
from .drawing import PC_CHOCH, PC_ENTRY, PC_FVG, PC_HTF_FVG

__all__ = ["PercocoEngine"]

_LONG = "#10b981"
_SHORT = "#ef4444"
_HTF = "#a855f7"
_FVG = "#eab308"


@dataclass
class _Pivot:
    price: float
    idx: int
    time: int


@dataclass
class _HtfFvg:
    long: bool
    top: float
    bot: float
    time: int        #: čas strednej sviečky (kreslenie)
    idx: int         #: index 15m sviečky, ktorá FVG potvrdila
    uid: str


@dataclass
class _Setup:
    long: bool
    entry: float
    stop: float
    take: float
    choch_idx: int
    fvg_top: float
    fvg_bot: float
    fvg_time: int
    uid: str


class PercocoEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: PercocoConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        tf = int(cfg.htfTF)
        if tf < self.chart_tf_minutes or tf % self.chart_tf_minutes:
            tf = -(-max(tf, self.chart_tf_minutes) // self.chart_tf_minutes) * self.chart_tf_minutes
        self.htf = tf
        self.agg = StructAggregator(tf, self.chart_tf_minutes)
        self._zone = ZoneInfo(cfg.tradeTZ)

        # ---- 15m ----
        hn = int(cfg.htfSwingLen)
        self.hbars: deque[Bar] = deque(maxlen=2 * hn + 4)
        self.h_idx = -1
        self.h_atr = 0.0
        self._h_tr: list[float] = []
        self.h_ph: _Pivot | None = None
        self.h_pl: _Pivot | None = None
        self.h_trend = 0
        self.h_fvgs: list[_HtfFvg] = []
        self._touch: dict[bool, int] = {True: -10**9, False: -10**9}   # posledný dotyk 15m FVG (long / short)

        # ---- graf ----
        n = int(cfg.swingLen)
        self.bars: deque[Bar] = deque(maxlen=max(600, int(cfg.setupMaxBars) + 200))
        self.idx = -1
        self.atr = 0.0
        self._tr: list[float] = []
        self.ph: _Pivot | None = None
        self.pl: _Pivot | None = None
        self.trend = 0
        self.setup: _Setup | None = None
        self._pending: tuple[str, int, float, _Setup] | None = None
        self._trade_ids: tuple[str, str] | None = None    #: obj_id TP / SL boxu bežiaceho obchodu
        self._day: tuple[int, int, int] | None = None
        self._trades_today = 0
        self._seeding = False

        self.warmup = Warmup(self.chart_tf_minutes).add(f"ATR {cfg.atrLen} + swingy grafu", int(cfg.atrLen) + 2 * n + 30)
        self.warmup.add_seeded(f"15m štruktúra a FVG ({tf}m)", 2 * hn + int(cfg.atrLen) + 200, tf, self._seed)
        self.required_history = self.warmup.chart_bars

    # ------------------------------------------------------------------ #
    # 15m
    # ------------------------------------------------------------------ #

    def _seed(self, bars, partial: Bar | None) -> None:
        self._seeding = True
        for b in bars:
            self._on_htf(b, None)
        self._seeding = False
        self.agg.prime(partial)

    def _on_htf(self, b: Bar, out: EngineOutput | None) -> None:
        cfg = self.cfg
        prev = self.hbars[-1] if self.hbars else None
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close), abs(b.low - prev.close))
        if self.h_atr > 0:
            self.h_atr += (tr - self.h_atr) / int(cfg.atrLen)
        else:
            self._h_tr.append(tr)
            if len(self._h_tr) >= int(cfg.atrLen):
                self.h_atr = sum(self._h_tr) / len(self._h_tr)
        self.hbars.append(b)
        self.h_idx += 1
        # trend: prieraz posledného swingu zavretím
        if self.h_ph is not None and b.close > self.h_ph.price:
            self.h_trend, self.h_ph = 1, None
        elif self.h_pl is not None and b.close < self.h_pl.price:
            self.h_trend, self.h_pl = -1, None
        # zánik FVG: zavretie za vzdialenou hranou alebo vek
        end_t = b.time + self.htf * 60_000
        alive = []
        for f in self.h_fvgs:
            dead = (b.close < f.bot) if f.long else (b.close > f.top)
            if dead or self.h_idx - f.idx > int(cfg.htfFvgMaxBars):
                if out is not None and cfg.showHtfFvg:
                    out.drawings.append(DrawUpdate(f.uid, "x2_ms", end_t))
                continue
            alive.append(f)
        self.h_fvgs = alive
        # nové FVG
        if len(self.hbars) >= 3:
            b0, b1, b2 = self.hbars[-1], self.hbars[-2], self.hbars[-3]
            m = cfg.htfFvgMinAtr.value * self.h_atr
            for long, top, bot in ((True, b0.low, b2.high), (False, b2.low, b0.high)):
                if top > bot and top - bot >= m and top - bot > 0:
                    uid = f"pc.h.{'u' if long else 'd'}.{b1.time}"
                    f = _HtfFvg(long, top, bot, b1.time, self.h_idx, uid)
                    self.h_fvgs.append(f)
                    if out is not None and cfg.showHtfFvg:
                        out.drawings.append(DrawBox(PC_HTF_FVG, b1.time, top, end_t, bot, _HTF,
                                                    fill_color=with_alpha(_HTF, 40), obj_id=uid,
                                                    text=f"15m FVG {'↑' if long else '↓'}"))
        # swingy (potvrdené `htfSwingLen` sviečkami vpravo)
        n = int(cfg.htfSwingLen)
        if len(self.hbars) >= 2 * n + 1:
            c = self.hbars[-n - 1]
            side = [self.hbars[-n - 1 - k] for k in range(1, n + 1)] + [self.hbars[-k] for k in range(1, n + 1)]
            ci = self.h_idx - n
            if all(c.high > x.high for x in side):
                self.h_ph = _Pivot(c.high, ci, c.time)
            if all(c.low < x.low for x in side):
                self.h_pl = _Pivot(c.low, ci, c.time)

    # ------------------------------------------------------------------ #
    # graf
    # ------------------------------------------------------------------ #

    def _bar_at(self, i: int) -> Bar | None:
        base = self.idx - len(self.bars) + 1
        return self.bars[i - base] if base <= i <= self.idx else None

    def _in_window(self, bar: Bar) -> bool:
        cfg = self.cfg
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return False
        if not cfg.useTradeWindow:
            return True
        m = local.hour * 60 + local.minute
        return cfg.window_start_minutes <= m < cfg.window_end_minutes

    def _plan(self, s: _Setup) -> TradePlan | None:
        cfg = self.cfg
        sl = abs(s.entry - s.stop)
        if sl < self.inst.tick_size * 2:
            return None
        min_sl = cfg.minSlDistance.resolve(self.inst, price=s.entry, atr=self.atr)
        if min_sl > 0 and sl < min_sl:
            return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG if s.long else Direction.SHORT, entry=self.inst.round_price(s.entry),
                         stop_loss=self.inst.round_price(s.stop), take_profit=self.inst.round_price(s.take),
                         qty=qty, sl_distance=sl)

    def _choch(self, long: bool, pivot: _Pivot, bar: Bar, out: EngineOutput) -> None:
        """CHoCH na grafe: hľadanie FVG v pohybe a nový setup."""
        cfg = self.cfg
        if self.cfg.showStructure:
            out.drawings.append(DrawLine(PC_CHOCH, pivot.time, pivot.price, bar.time + self.step_ms, pivot.price,
                                         _LONG if long else _SHORT, style=LineStyle.DASHED,
                                         obj_id=f"pc.c.{bar.time}", text="CHoCH"))
        if cfg.useHtfBias and self.h_trend != (1 if long else -1):
            return
        if cfg.useHtfPoi and self.idx - self._touch[long] > int(cfg.poiBars):
            return
        if (long and not cfg.allow_long) or (not long and not cfg.allow_short):
            return
        # pohyb CHoCH: od extrému po swingu (low pre long) po túto sviečku
        span = [(i, self._bar_at(i)) for i in range(pivot.idx, self.idx + 1)]
        span = [(i, b) for i, b in span if b is not None]
        if len(span) < 3:
            return
        ext_i, ext_b = (min(span, key=lambda x: x[1].low) if long else max(span, key=lambda x: x[1].high))
        ext = ext_b.low if long else ext_b.high
        m = cfg.fvgMinAtr.value * self.atr
        best = None
        for i in range(ext_i + 2, self.idx + 1):
            b0, b2, b1 = self._bar_at(i), self._bar_at(i - 2), self._bar_at(i - 1)
            if b0 is None or b2 is None:
                continue
            top, bot = (b0.low, b2.high) if long else (b2.low, b0.high)
            if top > bot and top - bot >= m:
                mid = (top + bot) / 2
                if (long and mid < bar.close) or (not long and mid > bar.close):
                    best = (top, bot, b1.time)
        if best is None:
            return
        top, bot, t = best
        k = cfg.entryPct / 100.0
        entry = (top - k * (top - bot)) if long else (bot + k * (top - bot))
        buf = cfg.slBufferAtr.value * self.atr
        stop = ext - buf if long else ext + buf
        risk = entry - stop if long else stop - entry
        if risk <= 0:
            return
        take = entry + cfg.rrRatio * risk if long else entry - cfg.rrRatio * risk
        self.setup = _Setup(long, entry, stop, take, self.idx, top, bot, t, f"pc.{bar.time}")

    def _swings(self, bar: Bar, out: EngineOutput) -> None:
        n = int(self.cfg.swingLen)
        # prieraz posledného swingu zavretím: BOS (v smere) alebo CHoCH (otočenie)
        if self.ph is not None and bar.close > self.ph.price:
            was = self.trend
            piv, self.ph, self.trend = self.ph, None, 1
            if was == -1:
                self._choch(True, piv, bar, out)
        elif self.pl is not None and bar.close < self.pl.price:
            was = self.trend
            piv, self.pl, self.trend = self.pl, None, -1
            if was == 1:
                self._choch(False, piv, bar, out)
        if len(self.bars) >= 2 * n + 1:
            c = self.bars[-n - 1]
            side = [self.bars[-n - 1 - k] for k in range(1, n + 1)] + [self.bars[-k] for k in range(1, n + 1)]
            ci = self.idx - n
            if all(c.high > x.high for x in side):
                self.ph = _Pivot(c.high, ci, c.time)
            if all(c.low < x.low for x in side):
                self.pl = _Pivot(c.low, ci, c.time)

    def _draw_trade(self, out: EngineOutput, s: _Setup, plan_entry: float, t: int) -> None:
        end = t + self.step_ms
        tp_id, sl_id = f"{s.uid}.tp", f"{s.uid}.sl"
        for kind, oid, level, color in ((DrawKind.TP_BOX, tp_id, s.take, _LONG), (DrawKind.SL_BOX, sl_id, s.stop, _SHORT)):
            out.drawings.append(DrawBox(kind, t, max(plan_entry, level), end, min(plan_entry, level), color,
                                        fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
        out.drawings.append(DrawBox(PC_FVG, s.fvg_time, s.fvg_top, end, s.fvg_bot, _FVG,
                                    fill_color=with_alpha(_FVG, 50), obj_id=f"{s.uid}.fvg", text="FVG"))
        out.drawings.append(DrawLabel(PC_ENTRY, t, plan_entry, f"{'LONG' if s.long else 'SHORT'} CHoCH + FVG", "#ffffff",
                                      style=LabelStyle.UP if s.long else LabelStyle.DOWN, above=not s.long,
                                      bg_color=_LONG if s.long else _SHORT, obj_id=f"{s.uid}.e"))
        self._trade_ids = (tp_id, sl_id)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        prev = self.bars[-1] if self.bars else None
        tr = bar.high - bar.low if prev is None else max(bar.high - bar.low, abs(bar.high - prev.close),
                                                           abs(bar.low - prev.close))
        if self.atr > 0:
            self.atr += (tr - self.atr) / int(cfg.atrLen)
        else:
            self._tr.append(tr)
            if len(self._tr) >= int(cfg.atrLen):
                self.atr = sum(self._tr) / len(self._tr)
        self.bars.append(bar)
        self.idx += 1
        idx = self.idx
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._zone)
        day = (local.year, local.month, local.day)
        if day != self._day:
            self._day, self._trades_today = day, 0
        flat = ctx.position_size == 0.0

        # ---- bežiaci obchod: boxy rastú ---------------------------------- #
        if self._trade_ids is not None:
            for oid in self._trade_ids:
                out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
            if flat and self._pending is None:
                self._trade_ids = None

        # ---- čakajúca limitka -------------------------------------------- #
        if self._pending is not None:
            oid, at, price, s = self._pending
            if oid in ctx.dropped_entry_ids:
                self._pending = None                       # obal ju zahodil (filter) — obchod nebol
            elif not flat or bar.low <= price <= bar.high:
                self._pending = None
                self.setup = None
                self._trades_today += 1
                self._draw_trade(out, s, price, bar.time)
            else:
                out.orders.append(OrderIntent(OrderAction.CANCEL, oid, at, reason="nevyplnené — posiela sa znova"))
                self._pending = None

        # ---- 15m: dotyk FVG pred aktualizáciou (FVG známe pred touto sviečkou) ---- #
        for f in self.h_fvgs:
            if bar.low <= f.top and bar.high >= f.bot:
                self._touch[f.long] = idx
        for hb in self.agg.push(bar):
            self._on_htf(hb, out)

        # ---- štruktúra grafu a CHoCH -------------------------------------- #
        self._swings(bar, out)          # nový CHoCH nahradí starý setup

        # ---- platnosť setupu --------------------------------------------- #
        s = self.setup
        if s is not None:
            long = s.long
            gone = ((bar.close < s.stop) if long else (bar.close > s.stop)) \
                or ((bar.high >= s.take) if long else (bar.low <= s.take)) \
                or idx - s.choch_idx > int(cfg.setupMaxBars) \
                or (self.trend == (-1 if long else 1) and idx > s.choch_idx)
            if gone or not self._in_window(bar):
                self.setup = None

        # ---- limitka ------------------------------------------------------ #
        s = self.setup
        if s is not None and flat and self._pending is None and self.atr > 0 and not self._seeding \
                and self._trades_today < cfg.maxTradesPerDay:
            plan = self._plan(s)
            if plan is None:
                self.setup = None
            else:
                oid = f"pc:{idx}"
                out.orders.append(OrderIntent(OrderAction.ENTRY, oid, idx, direction=plan.direction, plan=plan,
                                              order_type=OrderType.LIMIT,
                                              reason="CHoCH + FVG — limitka na stred FVG"))
                self._pending = (oid, idx, plan.entry, s)
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
