"""Engine ukážkovej stratégie: close nad/pod Donchian kanálom = breakout, SL z ATR, TP z RR.

Zámerne malý, ale používa presne to, čo každá stratégia v rámci potrebuje:
`BarHistory` (ATR), `OrderIntent` s `TradePlan`, kresby cez `DrawCommand`, kontext
pozície z adaptéra (`MarketContext.position_size`) a `EngineOutput.close_session`
na trhový výstup pri opačnom breakoute. Žiadny informatívny TF (htf je vždy None).
"""

from __future__ import annotations

from tradebot.core.drawing import DrawCommand, DrawLabel, DrawLine, LabelStyle
from tradebot.core.engine import EngineOutput
from tradebot.core.history import BarHistory
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

from .config import DemoBreakoutConfig, ExitMode
from .drawing import DC_LOWER, DC_UPPER, DEMO_ENTRY

__all__ = ["DemoBreakoutEngine"]

_LONG_COLOR = "#10b981"
_SHORT_COLOR = "#ef4444"
_CHANNEL_COLOR = "#3b82f6b3"


class DemoBreakoutEngine:
    """Bar-by-bar engine. Volaj `on_bar` presne raz na každý uzavretý bar grafu."""

    def __init__(self, cfg: DemoBreakoutConfig, inst: InstrumentSpec, chart_tf_minutes: int) -> None:
        self.cfg = cfg
        self.inst = inst
        self.chart_tf_minutes = chart_tf_minutes
        self.step_ms = chart_tf_minutes * 60_000
        #: kanál potrebuje `channelLen` uzavretých barov pred aktuálnym, ATR svoju dĺžku
        self.required_history = int(cfg.channelLen) + int(cfg.atrLen) + 8
        self.history = BarHistory(maxlen=self.required_history + 8, atr_len=int(cfg.atrLen))
        #: hrany kanála z barov PRED aktuálnym (Pine `ta.highest(high[1], n)`)
        self._upper: float | None = None
        self._lower: float | None = None
        #: posledný vstupný order a bar, na ktorom vznikol (na CANCEL nevyplnenej limitky)
        self._pending: tuple[str, int] | None = None
        self._last_direction: Direction | None = None

    # ------------------------------------------------------------------ #

    def _channel(self) -> tuple[float | None, float | None]:
        n = int(self.cfg.channelLen)
        if not self.history.has(n - 1):
            return None, None
        highs = [self.history[i].high for i in range(n)]
        lows = [self.history[i].low for i in range(n)]
        return max(highs), min(lows)

    def _plan(self, direction: Direction, entry: float, atr: float) -> TradePlan | None:
        sl_distance = self.cfg.slAtrMult.resolve(self.inst, price=entry, atr=atr)
        if sl_distance <= 0:
            return None
        sl_distance = self.inst.round_price(sl_distance) or sl_distance
        long = direction is Direction.LONG
        stop = entry - sl_distance if long else entry + sl_distance
        take = entry + sl_distance * self.cfg.rrRatio if long else entry - sl_distance * self.cfg.rrRatio
        qty = self.inst.qty_for_risk(self.cfg.riskDollar, sl_distance) if self.cfg.riskDollar > 0 else 1.0
        if qty <= 0:
            qty = float(self.inst.min_qty or 1.0)
        return TradePlan(
            direction=direction,
            entry=entry,
            stop_loss=self.inst.round_price(stop),
            take_profit=self.inst.round_price(take),
            qty=qty,
            sl_distance=sl_distance,
        )

    def on_bar(self, bar: Bar, htf=None, ctx: MarketContext | None = None) -> EngineOutput:
        ctx = ctx or MarketContext(in_trade_window=True)
        out = EngineOutput()
        upper, lower = self._upper, self._lower
        self.history.append(bar)
        atr = self.history.atr
        idx = self.history.bar_index

        if self.cfg.showChannel and upper is not None and lower is not None:
            out.drawings.append(DrawLine(DC_UPPER, bar.time, upper, bar.time + self.step_ms, upper,
                                         _CHANNEL_COLOR, obj_id=f"dcu.{bar.time}", text="Kanál hore"))
            out.drawings.append(DrawLine(DC_LOWER, bar.time, lower, bar.time + self.step_ms, lower,
                                         _CHANNEL_COLOR, obj_id=f"dcl.{bar.time}", text="Kanál dole"))

        # nevyplnená limitka z predchádzajúceho baru sa ruší — vstup má byť na cene breakoutu
        if self._pending is not None and ctx.position_size == 0.0 and idx - self._pending[1] >= 1:
            out.orders.append(OrderIntent(OrderAction.CANCEL, self._pending[0], self._pending[1], reason="nevyplnené"))
            self._pending = None

        long_break = upper is not None and atr > 0 and bar.close > upper
        short_break = lower is not None and atr > 0 and bar.close < lower and self.cfg.allowShort

        # opačný breakout zavrie otvorenú pozíciu (Pine `strategy.close(immediately=true)`)
        if self.cfg.exitMode is ExitMode.OPPOSITE and ctx.position_size != 0.0:
            if (ctx.position_size > 0 and short_break) or (ctx.position_size < 0 and long_break):
                out.close_session = True
                for order_id in ctx.open_order_ids:
                    out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason="opačný breakout"))

        if ctx.position_size == 0.0 and self._pending is None and (long_break or short_break):
            direction = Direction.LONG if long_break else Direction.SHORT
            plan = self._plan(direction, bar.close, atr)
            if plan is not None:
                order_id = f"demo:{idx}"
                out.orders.append(OrderIntent(OrderAction.ENTRY, order_id, idx, direction=direction, plan=plan,
                                              order_type=OrderType.MARKET, reason="breakout"))
                self._pending = (order_id, idx)
                self._last_direction = direction
                long = direction is Direction.LONG
                out.drawings.append(DrawLabel(
                    DEMO_ENTRY, bar.time, bar.low if long else bar.high, "LONG" if long else "SHORT",
                    "#ffffff", style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                    bg_color=_LONG_COLOR if long else _SHORT_COLOR, obj_id=f"demo_entry.{bar.time}",
                ))

        if ctx.position_size != 0.0:
            self._pending = None  # vyplnené — sledovanie preberá adaptér

        self._upper, self._lower = self._channel()
        return out

    def final_drawings(self, bar: Bar) -> list[DrawCommand]:
        return []
