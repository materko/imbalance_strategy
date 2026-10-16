"""Pomocníci NOA: čas New York, plán obchodu, kreslenie vstupu, výstupy v čase a seansový VWAP.

Prevzaté zo záložných stratégií (iCloud ZALOZNE-STRATEGIE, 8. 10. 2026) — každý balík má vlastnú kópiu.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tradebot.core.drawing import DrawBox, DrawKind, DrawLabel, DrawUpdate, LabelStyle, with_alpha
from tradebot.core.engine import EngineOutput
from tradebot.core.orders import MarketContext, OrderAction, OrderIntent
from tradebot.core.risk import TradePlan
from tradebot.core.types import Bar, Direction, InstrumentSpec, OrderType

NY = ZoneInfo("America/New_York")
LONG_COLOR = "#10b981"
SHORT_COLOR = "#ef4444"
NO_TP_R = 100.0   #: bez cieľa: TP tak ďaleko, že ho cena nedosiahne (obchod končí stopom alebo v čase)


def ny(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=NY)


def close_minute(bar: Bar, step_ms: int) -> tuple[tuple[int, int, int], int, int]:
    """(deň NY, minúta dňa pri zavretí baru, deň v týždni) — bar končiaci 16:00 má minútu 960."""
    t = ny(bar.time + step_ms)
    return (t.year, t.month, t.day), t.hour * 60 + t.minute, t.weekday()


class TradeHelper:
    """Plán, vstup market, výstupy CLOSE a kresba obchodu (štítok + TP / SL boxy rastú, kým obchod beží)."""

    def __init__(self, inst: InstrumentSpec, step_ms: int, prefix: str, entry_kind: DrawKind) -> None:
        self.inst = inst
        self.step_ms = step_ms
        self.prefix = prefix
        self.entry_kind = entry_kind
        self.boxes: list[str] = []
        self.was_in = False

    def plan(self, long: bool, entry: float, stop: float, take: float | None, qty: float) -> TradePlan | None:
        sl = abs(entry - stop)
        if sl < self.inst.tick_size * 2:
            return None
        if take is None:
            take = entry + NO_TP_R * sl if long else entry - NO_TP_R * sl
        return TradePlan(direction=Direction.LONG if long else Direction.SHORT, entry=self.inst.round_price(entry),
                         stop_loss=self.inst.round_price(stop), take_profit=self.inst.round_price(take),
                         qty=qty, sl_distance=sl)

    def enter(self, out: EngineOutput, bar: Bar, idx: int, plan: TradePlan, reason: str, label: str,
              show_tp: bool = True) -> None:
        long = plan.direction is Direction.LONG
        out.orders.append(OrderIntent(OrderAction.ENTRY, f"{self.prefix}:{idx}", idx, direction=plan.direction,
                                      plan=plan, order_type=OrderType.MARKET, reason=reason))
        t = bar.time + self.step_ms          # market sa plní na otvorení ďalšej sviečky
        end = t + self.step_ms
        self.boxes = []
        levels = [(DrawKind.SL_BOX, plan.stop_loss, SHORT_COLOR)]
        if show_tp:
            levels.insert(0, (DrawKind.TP_BOX, plan.take_profit, LONG_COLOR))
        for kind, level, color in levels:
            oid = f"{self.prefix}.{kind[:2]}.{t}"
            out.drawings.append(DrawBox(kind, t, max(plan.entry, level), end, min(plan.entry, level), color,
                                        fill_color=with_alpha(color, 80), obj_id=oid,
                                        text=f"{'TP' if kind == DrawKind.TP_BOX else 'SL'} {level:g}"))
            self.boxes.append(oid)
        out.drawings.append(DrawLabel(self.entry_kind, t, plan.entry, label, "#ffffff",
                                      style=LabelStyle.UP if long else LabelStyle.DOWN, above=not long,
                                      bg_color=LONG_COLOR if long else SHORT_COLOR, obj_id=f"{self.prefix}.e.{t}"))

    def track(self, out: EngineOutput, bar: Bar, ctx: MarketContext) -> None:
        """Boxy bežiaceho obchodu rastú doprava; po skončení obchodu prestanú."""
        if not self.boxes:
            return
        for oid in self.boxes:
            out.drawings.append(DrawUpdate(oid, "x2_ms", bar.time + self.step_ms))
        if ctx.position_size != 0.0:
            self.was_in = True
        elif self.was_in:
            self.boxes, self.was_in = [], False

    @staticmethod
    def close(out: EngineOutput, ctx: MarketContext, idx: int, reason: str) -> None:
        out.close_session = True
        for oid in ctx.open_order_ids:
            out.orders.append(OrderIntent(OrderAction.CLOSE, oid, idx, reason=reason))


class SessionVwapLite:
    """VWAP od začiatku seansy (typická cena × objem), každý deň od nuly."""

    def __init__(self) -> None:
        self.day = None
        self.pv = 0.0
        self.v = 0.0

    def push(self, day, bar: Bar) -> float | None:
        if day != self.day:
            self.day, self.pv, self.v = day, 0.0, 0.0
        tp = (bar.high + bar.low + bar.close) / 3.0
        self.pv += tp * bar.volume
        self.v += bar.volume
        return self.pv / self.v if self.v > 0 else None
