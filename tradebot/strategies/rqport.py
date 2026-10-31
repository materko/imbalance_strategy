"""Spoločné kúsky prepisov roboquant šablón (Rust `rq_sdk`, zadanie týždňa 31. 10. 2026).

Sedem stratégií (`lliq`, `tmr`, `sigma`, `nqprec`, `flashorb`, `wpr`, `orb15`) robí vstup aj výstup rovnako:
market na zavretí baru so stopom a cieľom, zavretie pozície v čase, boxy TP / SL ťahané do konca obchodu.
Tu je to raz; logiku signálu má každá stratégia vo svojom `engine.py`. Jadro ani adaptéry tento modul nepoznajú.
"""

from __future__ import annotations

from tradebot.core.drawing import DrawBox, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan, TrailingPlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

__all__ = ["LONG_COLOR", "SHORT_COLOR", "TradeDraw", "close_all", "market_entry"]

LONG_COLOR = "#22c55e"
SHORT_COLOR = "#ef4444"
#: cieľ „bez cieľa“ (predloha nemá TP) — 100 R, v praxi sa nikdy netrafí
NO_TP_R = 100.0


def close_all(out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
    """Zavrieť pozíciu trhom (predloha `ctx.close_position()`)."""
    out.close_session = True
    for order_id in ctx.open_order_ids:
        out.orders.append(OrderIntent(OrderAction.CLOSE, order_id, idx, reason=reason))


class TradeDraw:
    """Boxy TP / SL od vstupu, predlžované každým barom, kým obchod beží."""

    def __init__(self, step_ms: int) -> None:
        self.step_ms = step_ms
        self.boxes: list[str] = []
        self.was_in = False

    def tick(self, out: EngineOutput, bar: Bar, pos: float) -> None:
        if not self.boxes:
            return
        for oid in self.boxes:
            out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
        if pos != 0.0:
            self.was_in = True
        elif self.was_in:
            self.boxes, self.was_in = [], False

    def start(self, out: EngineOutput, bar: Bar, prefix: str, entry: float, stop: float, take: float,
              label_kind: str, label: str, long: bool, show_tp: bool = True) -> None:
        end = bar.time + self.step_ms
        self.boxes, self.was_in = [], False
        boxes = [(DrawKind.SL_BOX, stop, SHORT_COLOR)]
        if show_tp:
            boxes.insert(0, (DrawKind.TP_BOX, take, LONG_COLOR))
        for kind, level, color in boxes:
            bid = f"{prefix}.{kind[:2]}.{bar.time}"
            out.drawings.append(DrawBox(kind, bar.time, max(entry, level), end, min(entry, level), color,
                                        fill_color=with_alpha(color, 60), obj_id=bid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(bid)
        out.drawings.append(DrawLabel(label_kind, bar.time, entry, label, "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"{prefix}.e.{bar.time}"))


def market_entry(out: EngineOutput, cfg, inst: InstrumentSpec, bar: Bar, idx: int, prefix: str, long: bool,
                 stop: float, take: float | None, reason: str, trailing: TrailingPlan | None = None) -> TradePlan | None:
    """Vstup trhom na zavretí baru so stopom a cieľom; `take=None` = bez cieľa (100 R).

    Veľkosť: `fixedQty` → `qty`, inak z `riskDollar` a vzdialenosti stopu (predloha: $ alebo % účtu)."""
    entry = bar.close
    stop = inst.round_price(stop)
    risk = abs(entry - stop)
    if risk < inst.tick_size or (long and stop >= entry) or (not long and stop <= entry):
        return None
    if take is None:
        take = entry + risk * NO_TP_R if long else entry - risk * NO_TP_R
    take = inst.round_price(take)
    if (long and take <= entry) or (not long and take >= entry):
        return None
    qty = cfg.qty if cfg.fixedQty else inst.qty_for_risk(cfg.riskDollar, risk)
    if qty <= 0:
        return None
    plan = TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=entry, stop_loss=stop,
                     take_profit=take, qty=qty, sl_distance=risk, trailing=trailing)
    out.orders.append(OrderIntent(OrderAction.ENTRY, f"{prefix}:{idx}", idx, direction=plan.direction, plan=plan,
                                  order_type=OrderType.MARKET, reason=reason))
    return plan
