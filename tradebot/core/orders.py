"""Čo engine povie adaptéru: order intenty, udalosti stavu a kontext trhu.

Generické pre každú stratégiu. `OrderIntent.source_id` je identita zdroja signálu
(pri IBS uid zóny — `zone_uid` je alias), aby adaptér vedel spárovať CANCEL/CLOSE
s pôvodným ENTRY bez toho, aby poznal vnútro stratégie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .risk import TradePlan
from .types import Direction, OrderType

__all__ = ["OrderAction", "OrderIntent", "StateEvent", "MarketContext"]


class OrderAction(str, Enum):
    ENTRY = "entry"
    CANCEL = "cancel"
    #: Zavri otvorenu poziciu za trhovu cenu - Pine `strategy.close(immediately=true)`.
    CLOSE = "close"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """Čo má adaptér spraviť. Engine sám nikdy neobchoduje."""

    action: OrderAction
    order_id: str
    #: identita zdroja signálu (IBS: uid zóny)
    source_id: int = 0
    direction: Direction | None = None
    plan: TradePlan | None = None
    order_type: OrderType = OrderType.LIMIT
    reason: str = ""

    @property
    def zone_uid(self) -> int:
        """IBS názov toho istého poľa."""
        return self.source_id


@dataclass(frozen=True, slots=True)
class StateEvent:
    """Záznam prechodu — pre logy, diagnostiku a golden testy."""

    ts_ms: int
    zone_uid: int
    from_state: int
    to_state: int
    reason: str = ""


@dataclass
class MarketContext:
    """Čo o svete engine sám nevie a musí mu to povedať adaptér."""

    in_trade_window: bool
    #: > 0 long, < 0 short, 0 flat — Pine `strategy.position_size`
    position_size: float = 0.0
    #: Pine `dailyWinLimitReached` (IBS)
    daily_win_limit_reached: bool = False
    #: Pine `marketBias`: +1 bullish, -1 bearish, 0 neurčené (IBS)
    market_bias: int = 0
    #: id orderov, ktoré u brokera práve reálne bežia (Pine `strategy.opentrades`)
    open_order_ids: frozenset[str] = field(default_factory=frozenset)
