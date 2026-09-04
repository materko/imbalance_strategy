"""Stop loss, take profit, veľkosť pozície a trailing — Pine riadky 1944–2016.

Toto je miesto, kde sa z nájdeného vstupu stane konkrétny order.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import IBSConfig
from .history import BarHistory
from .types import Direction, InstrumentSpec

__all__ = ["TradePlan", "TrailingPlan", "swing_stop_loss", "build_trade_plan"]


@dataclass(frozen=True, slots=True)
class TrailingPlan:
    """Trailing parametre. Pine ich počíta v DVOCH jednotkách naraz — to nie je omyl.

    `strategy.exit()` v TradingView očakáva **ticky**, zatiaľ čo JSON pre PickMyTrade
    (a teda reálny broker) očakáva **cenové body**. Keď sa to nerozlíši, trailing na
    grafe funguje a u brokera nie.
    """

    activation_price_distance: float  # cenové body
    offset_price_distance: float  # cenové body
    update_frequency: float  # cenové body
    activation_ticks: float
    offset_ticks: float

    @classmethod
    def build(cls, cfg: IBSConfig, inst: InstrumentSpec, sl_distance: float) -> "TrailingPlan | None":
        if not cfg.enableTrailing or sl_distance <= 0 or inst.tick_size <= 0:
            return None
        activation = cfg.trailActivationR * sl_distance
        offset = cfg.trailOffsetR * sl_distance
        return cls(
            activation_price_distance=activation,
            offset_price_distance=offset,
            update_frequency=offset * (cfg.trailFreqPct / 100.0),
            activation_ticks=activation / inst.tick_size,
            offset_ticks=offset / inst.tick_size,
        )


@dataclass(frozen=True, slots=True)
class TradePlan:
    """Hotový plán obchodu — presne to, čo ide do `strategy.entry` + `strategy.exit`."""

    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    qty: float
    sl_distance: float
    trailing: TrailingPlan | None = None

    @property
    def risk_reward(self) -> float:
        tp_distance = abs(self.take_profit - self.entry)
        return tp_distance / self.sl_distance if self.sl_distance > 0 else 0.0


def swing_stop_loss(
    history: BarHistory,
    direction: Direction,
    cfg: IBSConfig,
    inst: InstrumentSpec,
    *,
    zone_top: float,
    zone_bot: float,
    atr: float = 0.0,
) -> float:
    """Pine riadky 1952–1966 — SL z najextrémnejšieho swingu za `slLookback` barov.

    Keď v histórii nie je ani jeden bar (`slSwing` ostane `na`), Pine spadne späť na
    hranicu zóny — `bot` pre LONG, `top` pre SHORT.
    """
    swing: float | None = None
    for lb in range(cfg.slLookback):
        if not history.has(lb):
            break
        bar = history[lb]
        if direction is Direction.LONG:
            if swing is None or bar.low < swing:
                swing = bar.low
        else:
            if swing is None or bar.high > swing:
                swing = bar.high

    buffer = cfg.slBufferTicks.resolve(inst, price=history.current.close, atr=atr)
    if direction is Direction.LONG:
        return (zone_bot if swing is None else swing) - buffer
    return (zone_top if swing is None else swing) + buffer


def build_trade_plan(
    direction: Direction,
    entry: float,
    stop_loss: float,
    cfg: IBSConfig,
    inst: InstrumentSpec,
) -> TradePlan:
    """Dopočíta TP z `rrRatio`, veľkosť pozície a trailing.

    TP sa v Pine počíta **vždy**, aj keď order nakoniec von nepôjde — aby sa dali
    nakresliť TP/SL boxy aj pre neúspešný pokus.
    """
    sl_distance = (entry - stop_loss) if direction is Direction.LONG else (stop_loss - entry)

    if direction is Direction.LONG:
        take_profit = entry + sl_distance * cfg.rrRatio
    else:
        take_profit = entry - sl_distance * cfg.rrRatio

    qty = cfg.position_qty(inst, cfg.maxLossDollar, sl_distance) if cfg.maxLossDollar > 0 else 1.0

    return TradePlan(
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        qty=qty,
        sl_distance=sl_distance,
        trailing=TrailingPlan.build(cfg, inst, sl_distance),
    )
