"""Engine Volt Break: long, keď 30m sviečka zavrie nad „noise" hranicou aj nad VWAP.

Doslovný port Pine skriptu (`docs/sources/volt_break.pine`). Časy CT:

  1. Nový deň (polnoc CT): open prvého baru = open o polnoci, Noise Up = open + `noisePct` %
     priemerného ATR (`avgatr`, za `avgLen` seáns / dní). VWAP (hlc3) od polnoci CT.
  2. Signál: bar sa zatvára v okne `startHHMM`–`endHHMM`, pozícia plochá, menej než `maxTrades`
     obchodov dňa, zavretie nad Noise Up aj nad VWAP. Po výstupe môže vzniknúť ďalší.
  3. Vstup market na otvorení ďalšej sviečky. TP `tpUsd`, SL `slUsd` (v $ na kontrakt, prepočet
     cez `usdPerPoint`) od ceny vstupu — tu od zavretia signálnej sviečky.
  4. Časový exit na zavretí baru, ktorý sa zatvára v `endHHMM` alebo neskôr (pred 16:00 CT).
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

from .avgatr import SESSION_END_MIN, DailyAvgAtr, SessionAvgAtr
from .config import AtrSource, VoltBreakConfig, hhmm_minutes
from .drawing import VB_ENTRY, VB_NOISE, VB_VWAP

__all__ = ["VoltBreakEngine"]

_CT = "America/Chicago"
_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_BOX_BARS = 6


class VoltBreakEngine:
    def __init__(self, cfg: VoltBreakConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = max(1, int(chart_tf_minutes))
        self.step_ms = self.chart_tf_minutes * 60_000
        self.zone = ZoneInfo(_CT)
        self.start = hhmm_minutes(cfg.startHHMM)
        self.end = hhmm_minutes(cfg.endHHMM)
        self.vwap = SessionVwap(self.chart_tf_minutes, start_minutes=0, end_minutes=24 * 60, tz=_CT)
        self.sess_atr = SessionAvgAtr(cfg.atrLen, cfg.avgLen)
        self.daily_atr = DailyAvgAtr(cfg.atrLen, cfg.avgLen)
        #: priemerný ATR potrebuje avgLen seáns — to je stav, nie predhistória grafu (beh ho dobehne sám)
        self.warmup = Warmup(self.chart_tf_minutes).add("bez predhistórie", 2)
        self.required_history = self.warmup.chart_bars
        self.history = BarHistory(maxlen=8, atr_len=14)
        self._prev_day = None
        self.sess_open: float | None = None
        self.noise_up: float | None = None
        self.trades_today = 0
        self._last_vwap: tuple[int, float] | None = None

    @property
    def avg_atr(self) -> float | None:
        return self.daily_atr.value if self.cfg.atrSource is AtrSource.DAILY else self.sess_atr.value

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        cfg = self.cfg
        self.history.append(bar)
        idx = self.history.bar_index

        local = datetime.fromtimestamp(bar.time / 1000, tz=self.zone)
        close_local = datetime.fromtimestamp((bar.time + self.step_ms) / 1000, tz=self.zone)
        bar_min = local.hour * 60 + local.minute
        close_min = close_local.hour * 60 + close_local.minute
        day = local.date()

        self.sess_atr.push(bar, bar_min)
        self.daily_atr.push(bar, local)
        vw = self.vwap.push(bar)

        if self._prev_day is None or day != self._prev_day:
            avg = self.avg_atr
            self.sess_open = bar.open
            self.noise_up = None if avg is None else bar.open + cfg.noisePct / 100.0 * avg
            self.trades_today = 0
            self._last_vwap = None
            if cfg.showLevels and self.noise_up is not None:
                right = bar.time + max(self.end - bar_min, self.chart_tf_minutes) * 60_000
                out.drawings.append(DrawLine(VB_NOISE, bar.time, self.noise_up, right, self.noise_up, "#f59e0b",
                                             obj_id=f"vb_noise.{bar.time}", text="Noise Up"))
        self._prev_day = day

        if cfg.showLevels and vw is not None and bar_min < SESSION_END_MIN:
            end_ms = bar.time + self.step_ms
            prev, self._last_vwap = self._last_vwap, (end_ms, vw)
            if prev is not None:
                out.drawings.append(DrawLine(VB_VWAP, prev[0], prev[1], end_ms, vw, "#3b82f6",
                                             obj_id=f"vb_vwap.{end_ms}", text="VWAP"))

        flat = ctx.position_size == 0.0
        in_window = self.start <= close_min < self.end
        if (in_window and flat and self.trades_today < int(cfg.maxTrades) and self.noise_up is not None
                and bar.close > self.noise_up and vw is not None and bar.close > vw):
            plan = self._plan(bar)
            if plan is not None:
                self.trades_today += 1
                out.orders.append(OrderIntent(OrderAction.ENTRY, f"vb:{idx}", idx, direction=Direction.LONG,
                                              plan=plan, order_type=OrderType.MARKET,
                                              reason="zavretie nad Noise Up aj VWAP"))
                out.drawings.append(DrawLabel(VB_ENTRY, bar.time, bar.low, "LONG", "#ffffff", style=LabelStyle.UP,
                                              above=False, bg_color=_LONG_COLOR, obj_id=f"vb_entry.{bar.time}"))
                out.drawings += self._trade_boxes(bar, plan)

        if cfg.useTimeExit and not flat and close_min >= self.end and bar_min < SESSION_END_MIN:
            out.close_session = True
            for order_id in ctx.open_order_ids:
                out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="časový exit"))
        return out

    def _plan(self, bar: Bar) -> TradePlan | None:
        cfg = self.cfg
        sl_distance = cfg.sl_points
        if sl_distance <= 0:
            return None
        entry = bar.close
        qty = cfg.position_qty(self.inst, cfg.riskDollar, sl_distance) if cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(direction=Direction.LONG, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(entry - sl_distance),
                         take_profit=self.inst.round_price(entry + cfg.tp_points),
                         qty=qty, sl_distance=sl_distance)

    def _trade_boxes(self, bar: Bar, plan: TradePlan) -> list[DrawCommand]:
        right = bar.time + _BOX_BARS * self.step_ms
        return [
            DrawBox(kind=kind, x1_ms=bar.time, y1=max(plan.entry, price), x2_ms=right,
                    y2=min(plan.entry, price), border_color=color, fill_color=color + "40",
                    border_width=0, obj_id=f"vb{bar.time}.{kind.value}")
            for kind, price, color in ((DrawKind.TP_BOX, plan.take_profit, _LONG_COLOR),
                                       (DrawKind.SL_BOX, plan.stop_loss, _SHORT_COLOR))
        ]

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
