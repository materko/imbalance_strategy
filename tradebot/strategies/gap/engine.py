"""Engine Gap Fill: otváracia medzera sa vypĺňa častejšie, než nie — a čím menšia, tým skôr.

Priebeh jedného dňa:

  1. na prvom bare seansy sa zmeria **medzera** = dnešný open − včerajší close seansy
  2. medzera sa preverí filtrami: veľkosť v ATR, smer, či open padol do včerajšieho rozsahu
  3. podľa ``entryMode`` sa vstúpi hneď, po potvrdzovacej sviečke, alebo na retestte
  4. **obchoduje sa proti medzere** — gap up sa predáva, gap down kupuje
  5. cieľ je výplň (včerajší close) alebo jej podiel, stop podľa ``slMode``
  6. obchod končí na cieli, stope, po ``maxHoldMinutes`` alebo na konci seansy

Čísla v defaultoch sú z merania na 2 791 dňoch NQ (2015–2025): medzera pod 0,3 ATR sa
vyplní v 77,8 % dní (s potvrdením prvej 15m sviečky až v 93 %), nad 1,2 ATR len v 8,2 %.
Medián času do výplne je 18 minút. Pohyb proti sebe má medián 0,34 ATR, 90. percentil
0,97 ATR — odtiaľ default stopu 1,0 ATR.

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

from .config import EntryMode, GapConfig, SlMode, TpMode
from .drawing import GAP_BOX, GAP_ENTRY, GAP_TARGET

__all__ = ["GapEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_GAP_COLOR = "#f59e0b33"
_TARGET_COLOR = "#10b981b3"


@dataclass
class _Day:
    """Čo si engine pamätá o jednom dni."""

    key: tuple[int, int, int] | None = None
    #: uzavretá seansa predchádzajúceho dňa
    prev_close: float | None = None
    prev_high: float | None = None
    prev_low: float | None = None
    #: rozpracovaná seansa dneška
    high: float | None = None
    low: float | None = None
    close: float | None = None
    #: dnešná medzera
    open_price: float = 0.0
    open_ms: int = 0
    gap: float = 0.0
    direction: Direction | None = None
    ok: bool = False
    traded: bool = False
    #: potvrdenie a retest
    confirmed_bar: int = -1
    open_bar_high: float = 0.0
    open_bar_low: float = 0.0


class GapEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: GapConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self._tz = ZoneInfo(cfg.sessionTZ)

        self.required_history = int(cfg.atrLen) + 16
        self.history = BarHistory(maxlen=self.required_history + 16, atr_len=int(cfg.atrLen))

        self.day = _Day()
        self._pending: tuple[str, int] | None = None
        self._entry_bar: int = -1

    # ------------------------------------------------------------------ #

    def _minutes(self, local: datetime) -> int:
        return local.hour * 60 + local.minute

    def _day_ref(self, atr: float) -> float:
        """Denná mierka pre prahy medzery a stopu.

        Meranie, z ktorého stratégia vychádza, počíta veľkosť medzery v násobkoch
        **denného** ATR. ATR grafu je o rád menšie (na 5m baroch ~15 bodov oproti
        ~300 dennému rozsahu), takže prah `0,3` by v ňom zahodil každú medzeru.
        Ako denná mierka slúži rozsah predchádzajúcej seansy; kým nie je, berie sa
        ATR grafu prepočítané na počet barov v dni.
        """
        d = self.day
        if d.prev_high is not None and d.prev_low is not None and d.prev_high > d.prev_low:
            return d.prev_high - d.prev_low
        return atr * (390.0 / self.chart_tf_minutes) ** 0.5

    def _roll_day(self, day: tuple[int, int, int]) -> None:
        """Nový deň: to, čo bolo dnes, sa stáva včerajškom."""
        d = self.day
        d.prev_close, d.prev_high, d.prev_low = d.close, d.high, d.low
        d.key = day
        d.high = d.low = d.close = None
        d.gap = 0.0
        d.direction = None
        d.ok = False
        d.traded = False
        d.confirmed_bar = -1

    # ------------------------------------------------------------------ #

    def _target_price(self, entry: float, sl_distance: float, atr: float) -> float:
        cfg, d = self.cfg, self.day
        long = d.direction is Direction.LONG
        if cfg.tpMode is TpMode.GAP:
            dist = abs(d.gap) * (cfg.targetPct / 100.0)
        elif cfg.tpMode is TpMode.RR:
            dist = sl_distance * cfg.rrRatio
        else:
            dist = cfg.tpAtrMult.resolve(self.inst, price=entry, atr=atr)
        return entry + dist if long else entry - dist

    def _stop_price(self, entry: float, atr: float) -> float:
        cfg, d = self.cfg, self.day
        long = d.direction is Direction.LONG
        if cfg.slMode is SlMode.GAP_MULT:
            dist = abs(d.gap) * cfg.slGapMult
        elif cfg.slMode is SlMode.OPEN_BAR:
            base = d.open_bar_low if long else d.open_bar_high
            return base
        else:
            dist = cfg.slAtrMult.resolve(self.inst, price=entry, atr=self._day_ref(atr))
        return entry - dist if long else entry + dist

    def _plan(self, entry: float, atr: float) -> TradePlan | None:
        d = self.day
        if d.direction is None:
            return None
        stop = self._stop_price(entry, atr)
        sl_distance = abs(entry - stop)
        if sl_distance < self.inst.tick_size * 2:
            return None
        # Rozšírenie portu: obchod s príliš tesným SL sa preskočí. Poplatok je percento
        # z nominálu a zisk rastie s R, takže tesné stopy majú najhorší pomer edge k poplatku.
        min_sl = self.cfg.minSlDistance.resolve(self.inst, price=entry, atr=atr)
        if min_sl > 0 and sl_distance < min_sl:
            return None
        take = self._target_price(entry, sl_distance, atr)
        long = d.direction is Direction.LONG
        if (long and take <= entry) or (not long and take >= entry):
            return None

        qty = (self.cfg.position_qty(self.inst, self.cfg.riskDollar, sl_distance)
               if self.cfg.riskDollar > 0 else 1.0)
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)

        trailing = None
        if self.cfg.enableTrailing:
            act = sl_distance * self.cfg.trailActivationR
            off = sl_distance * self.cfg.trailOffsetR
            tick = self.inst.tick_size or 1.0
            trailing = TrailingPlan(activation_price_distance=act, offset_price_distance=off,
                                    activation_ticks=act / tick, offset_ticks=off / tick)
        return TradePlan(direction=d.direction, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop),
                         take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl_distance, trailing=trailing)

    # ------------------------------------------------------------------ #

    def _measure_gap(self, bar: Bar, atr: float, out: EngineOutput) -> None:
        """Prvý bar seansy: zmeraj medzeru a rozhodni, či sa dá obchodovať."""
        cfg, d = self.cfg, self.day
        d.open_price = bar.open
        d.open_ms = bar.time
        d.open_bar_high, d.open_bar_low = bar.high, bar.low
        if d.prev_close is None or atr <= 0:
            return
        d.gap = bar.open - d.prev_close
        size = abs(d.gap)
        ref = self._day_ref(atr)
        lo = cfg.minGapAtr.resolve(self.inst, price=bar.open, atr=ref)
        hi = cfg.maxGapAtr.resolve(self.inst, price=bar.open, atr=ref)
        if not (lo <= size <= hi):
            return
        up = d.gap > 0
        if up and not cfg.trade_gap_up:
            return
        if not up and not cfg.trade_gap_down:
            return
        # Otvorenie vnútri včerajšieho rozsahu sa vypĺňa v 70,4 % dní, mimo neho v ~45 %.
        if cfg.requireInsideRange and d.prev_high is not None and d.prev_low is not None:
            if not (d.prev_low <= bar.open <= d.prev_high):
                return
        d.direction = Direction.SHORT if up else Direction.LONG
        d.ok = True

        if cfg.showGap:
            top, bottom = max(bar.open, d.prev_close), min(bar.open, d.prev_close)
            out.drawings.append(DrawBox(
                GAP_BOX, bar.time - self.step_ms, top, bar.time + self.step_ms * 40, bottom,
                _GAP_COLOR, obj_id=f"gap.{d.key}", text=f"Medzera {size / ref:.2f} dňa"))
        if cfg.showTarget:
            out.drawings.append(DrawLine(
                GAP_TARGET, bar.time, d.prev_close, bar.time + self.step_ms * 40, d.prev_close,
                _TARGET_COLOR, obj_id=f"gapt.{d.key}", text="Výplň medzery"))

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg, d = self.cfg, self.day

        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index
        local = datetime.fromtimestamp(bar.time / 1000, tz=self._tz)
        if cfg.weekdaysOnly and local.weekday() >= 5:
            return out
        minutes = self._minutes(local)
        start = cfg.sessionStartH * 60 + cfg.sessionStartM
        end = cfg.sessionEndH * 60 + cfg.sessionEndM
        in_session = start <= minutes < end

        day = (local.year, local.month, local.day)
        first_bar = False
        if day != d.key:
            self._roll_day(day)
            first_bar = in_session
        elif in_session and d.high is None:
            first_bar = True

        if in_session:
            d.high = bar.high if d.high is None else max(d.high, bar.high)
            d.low = bar.low if d.low is None else min(d.low, bar.low)
            d.close = bar.close

        # ---- zrušenie nevyplnenej limitky ------------------------------- #
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1],
                                          reason="nevyplnené"))
            self._pending = None
        if ctx.position_size != 0.0:
            self._pending = None

        # ---- výstupy na čas --------------------------------------------- #
        if ctx.position_size != 0.0:
            held = (idx - self._entry_bar) * self.chart_tf_minutes
            if cfg.maxHoldMinutes > 0 and held >= cfg.maxHoldMinutes:
                out.close_session = True
                for oid in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx,
                                                  reason="vypršal čas na výplň"))
                return out
            if cfg.closeAtSessionEnd and not in_session:
                out.close_session = True
                for oid in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx,
                                                  reason="koniec seansy"))
                return out
            return out

        if first_bar:
            self._measure_gap(bar, atr, out)
            if cfg.entryMode is EntryMode.OPEN and d.ok:
                self._enter(out, bar.close, atr, idx, bar, OrderType.MARKET, "výplň medzery")
            return out

        if not (in_session and d.ok and not d.traded) or self._pending is not None:
            return out
        if cfg.entryWindowMinutes > 0 and minutes > start + cfg.entryWindowMinutes:
            return out

        long = d.direction is Direction.LONG
        # ---- potvrdenie: sviečka musí zavrieť smerom k výplni ------------ #
        if d.confirmed_bar < 0:
            need = max(1, int(cfg.confirmMinutes) // self.chart_tf_minutes)
            since = (minutes - start) // self.chart_tf_minutes
            if since < need:
                return out
            toward = bar.close > bar.open if long else bar.close < bar.open
            if not toward:
                return out
            d.confirmed_bar = idx
            if cfg.entryMode is EntryMode.CONFIRM:
                self._enter(out, bar.close, atr, idx, bar, OrderType.MARKET,
                            "potvrdená výplň medzery")
            return out

        # ---- retest otváracej ceny --------------------------------------- #
        if cfg.entryMode is EntryMode.RETEST:
            if idx - d.confirmed_bar > cfg.retestMaxBars:
                d.ok = False
                return out
            touched = bar.low <= d.open_price if long else bar.high >= d.open_price
            if touched:
                self._enter(out, d.open_price, atr, idx, bar, OrderType.LIMIT,
                            "retest otváracej ceny")
        return out

    # ------------------------------------------------------------------ #

    def _enter(self, out: EngineOutput, entry: float, atr: float, idx: int, bar: Bar,
               order_type: OrderType, reason: str) -> None:
        plan = self._plan(entry, atr)
        if plan is None:
            self.day.ok = False
            return
        order_id = f"gap:{idx}"
        out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx,
                                      direction=self.day.direction, plan=plan,
                                      order_type=order_type, reason=reason))
        self._pending = (order_id, idx)
        self._entry_bar = idx
        self.day.traded = True
        long = self.day.direction is Direction.LONG
        out.drawings.append(DrawLabel(
            GAP_ENTRY, bar.time, bar.low if long else bar.high,
            "LONG výplň" if long else "SHORT výplň", "#ffffff",
            style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
            bg_color=_LONG_COLOR if long else _SHORT_COLOR,
            obj_id=f"gap_entry.{bar.time}"))

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
