"""Engine VWAP ADX: pullback k VWAP po prerazení opening rangu, vstup keď ADX prestane rásť.

Doslovný port Pine skriptu (`docs/sources/vwap_adx.pine`), len long. Priebeh dňa (časy CT):

  1. `rthStart` = prvý bar dňa o `orStartHHMM` alebo neskôr — nový opening range (high/low),
     vynulujú sa stavy „nabitá" a „dotyk". Do `orEndHHMM` sa range rozširuje.
  2. VWAP (hlc3) ukotvený na `rthStart` alebo na polnoc CT (`vwapAnchor`) — `tradebot.core.vwap`.
  3. Po konci rangu, kým sa bar nezatvorí v `exitHHMM`:
     zavretie nad high rangu = **nabitá**; potom low ≤ VWAP = **dotyk** (oboje aj v tej istej sviečke).
  4. Signál: nabitá + dotyk + zavretie nad VWAP + ADX > `adxMin` a ADX ≤ ADX predošlého baru,
     pozícia plochá, menej než `maxTrades` obchodov od `rthStart`. Po signáli sa dotyk vynuluje.
  5. Vstup market (na otvorení ďalšej sviečky), TP = najvyšší high posledných `tpBars` barov,
     SL = najnižší low posledných `slBars` barov (vrátane signálnej). Úrovne sú pevné.
  6. Časový exit: otvorená pozícia sa zatvorí na zavretí baru, ktorý sa zatvára v `exitHHMM`
     alebo neskôr (len pred 17:00 CT).

ADX je Pine `ta.dmi(adxLen, adxLen)` — tá istá implementácia ako v IBS (`DMI`).
Engine je čistý: žiadne I/O, žiadny globálny stav, všetko je v ``self``.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawCommand, DrawKind, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType
from tradebot.core.vwap import SessionVwap
from tradebot.core.warmup import Warmup
from tradebot.strategies.ibs.ta.trend import DMI

from .config import VwapAdxConfig, VwapAnchor, hhmm_minutes
from .drawing import VA_ENTRY, VA_RANGE, VA_VWAP

__all__ = ["VwapAdxEngine"]

_CT = "America/Chicago"
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_VWAP_COLOR = "#3b82f6"
_RANGE_COLOR = "#f59e0b"
_BOX_BARS = 30
#: VWAP sa kreslí raz za toľko minút (na 1m grafe by úsečka za každý bar bola zbytočne veľa kresieb)
_VWAP_STEP_MIN = 5


class VwapAdxEngine:
    """Bar-by-bar engine. Volaj ``on_bar`` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: VwapAdxConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_CT)
        self.or_s = hhmm_minutes(cfg.orStartHHMM)
        self.or_e = hhmm_minutes(cfg.orEndHHMM)
        self.ex = hhmm_minutes(cfg.exitHHMM)

        if cfg.vwapAnchor is VwapAnchor.MIDNIGHT:
            self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=0, end_minutes=24 * 60, tz=_CT)
        else:
            # začiatok = koniec: celý deň je jedna seansa, ktorá sa nuluje na prvom bare o orStart
            # alebo neskôr — presne Pine `rthStart` (aj nedeľné otvorenie 17:00 po víkende)
            self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=self.or_s,
                                    end_minutes=self.or_s, tz=_CT)
        self.dmi = DMI(int(cfg.adxLen), int(cfg.adxLen))

        n = max(int(cfg.tpBars), int(cfg.slBars))
        self.warmup = (Warmup(self.chart_tf_minutes)
                       .add(f"ADX {cfg.adxLen}", self.dmi.warmup_bars)
                       .add(f"TP/SL {n} barov", n))
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=n + 16, atr_len=14)

        self._prev_min: int | None = None
        self._prev_day = None
        self._prev_adx: float | None = None
        self.or_h: float | None = None
        self.or_l: float | None = None
        self._or_start_ms: int | None = None
        self._range_drawn = False
        self.armed = False
        self.touched = False
        self.trades_today = 0
        self._last_vwap: tuple[int, float] | None = None

    # ------------------------------------------------------------------ #

    def _plan(self, bar: Bar) -> TradePlan | None:
        cfg = self.cfg
        tp = max(self.history[i].high for i in range(min(int(cfg.tpBars), len(self.history))))
        sl = min(self.history[i].low for i in range(min(int(cfg.slBars), len(self.history))))
        entry = bar.close
        sl_distance = entry - sl
        if sl_distance <= 0:
            return None
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(sl), take_profit=self.inst.round_price(tp),
                         qty=qty, sl_distance=sl_distance)

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg

        self.history.append(bar)
        idx = self.history.bar_index
        adx = self.dmi.push(bar)
        vw = self.vwap.push(bar)

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        close_local = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=self.zone)
        bar_min = local.hour * 60 + local.minute
        close_min = close_local.hour * 60 + close_local.minute
        day = local.date()
        new_day = self._prev_day is None or day != self._prev_day
        rth_start = bar_min >= self.or_s and (new_day or (self._prev_min is not None and self._prev_min < self.or_s))

        # ---- opening range ---------------------------------------------- #
        if rth_start:
            self.or_h, self.or_l = bar.high, bar.low
            self.armed = self.touched = False
            self.trades_today = 0
            self._or_start_ms = bar.time
            self._range_drawn = False
            self._last_vwap = None
        elif self.or_s <= bar_min < self.or_e and self.or_h is not None:
            self.or_h = max(self.or_h, bar.high)
            self.or_l = min(self.or_l, bar.low)

        after_or = bar_min >= self.or_e and close_min < self.ex
        adx_ok = (adx is not None and self._prev_adx is not None
                  and adx > cfg.adxMin and adx <= self._prev_adx)

        if after_or and self.or_h is not None:
            if not self.armed and bar.close > self.or_h:
                self.armed = True
            if self.armed and vw is not None and bar.low <= vw:
                self.touched = True

        out.drawings += self._draw(bar, bar_min, vw)

        # ---- časový exit -------------------------------------------------- #
        flat = ctx.position_size == 0.0
        if cfg.useTimeExit and not flat and close_min >= self.ex and bar_min < 17 * 60:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="časový exit"))

        # ---- signál -------------------------------------------------------- #
        if (after_or and self.armed and self.touched and vw is not None and bar.close > vw and adx_ok
                and flat and self.trades_today < int(cfg.maxTrades)):
            self.touched = False  # ďalší obchod (ak je povolený) potrebuje nový pullback
            plan = self._plan(bar)
            if plan is not None:
                self.trades_today += 1
                out.orders.append(OrderIntent(OrderAction.ENTRY, f"va:{idx}", idx, direction=Direction.LONG,
                                              plan=plan, order_type=OrderType.MARKET,
                                              reason="pullback k VWAP po prerazení rangu, ADX prestal rásť"))
                out.drawings.append(DrawLabel(VA_ENTRY, bar.time, bar.low, "LONG", "#ffffff",
                                              style=LabelStyle.UP, above=False, bg_color=_LONG_COLOR,
                                              obj_id=f"va_entry.{bar.time}"))
                out.drawings += self._trade_boxes(bar, plan)

        self._prev_min, self._prev_day, self._prev_adx = bar_min, day, adx
        return out

    # ------------------------------------------------------------------ #

    def _draw(self, bar: Bar, bar_min: int, vw: float | None) -> list[DrawCommand]:
        cmds: list[DrawCommand] = []
        cfg = self.cfg
        in_day = self.or_s <= bar_min < self.ex
        if cfg.showRange and not self._range_drawn and bar_min >= self.or_e and self.or_h is not None \
                and self._or_start_ms is not None:
            right = self._or_start_ms + (self.ex - self.or_s) * 60_000
            cmds.append(DrawBox(kind=VA_RANGE, x1_ms=self._or_start_ms, y1=self.or_h, x2_ms=right, y2=self.or_l,
                                border_color=_RANGE_COLOR, fill_color=_RANGE_COLOR + "18", border_width=1,
                                obj_id=f"va_range.{self._or_start_ms}"))
            self._range_drawn = True
        if cfg.showVwap and vw is not None and in_day and bar_min % _VWAP_STEP_MIN == 0:
            end = bar.time + self.step_ms
            prev, self._last_vwap = self._last_vwap, (end, vw)
            if prev is not None:
                cmds.append(DrawLine(VA_VWAP, prev[0], prev[1], end, vw, _VWAP_COLOR,
                                     obj_id=f"va_vwap.{end}", text="VWAP"))
        return cmds

    def _trade_boxes(self, bar: Bar, plan: TradePlan) -> list[DrawCommand]:
        right = bar.time + _BOX_BARS * self.step_ms
        return [
            DrawBox(kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                    y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                    border_width=0, obj_id=f"va{bar.time}.{kind.value}")
            for kind, price, color in (
                (DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR),
            )
        ]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
