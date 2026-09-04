"""Stop loss, take profit, veľkosť pozície a trailing — Pine riadky 1944–2016.

Toto je miesto, kde sa z nájdeného vstupu stane konkrétny order.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import IBSConfig
from .history import BarHistory
from .types import Direction, InstrumentSpec

__all__ = [
    "TradePlan",
    "TrailingPlan",
    "extreme_before_stop",
    "swing_stop_loss",
    "build_trade_plan",
]


def extreme_before_stop(bar_open: float, high: float, low: float, *, long: bool) -> bool:
    """Dosiahne sviečka priaznivý extrém skôr, než tú stranu, kde je stop?

    Pravidlo broker emulátora z TradingView: **bližší extrém k otváracej cene sa
    dosiahne skôr**. Pri pevnom SL/TP je to jedno — obe úrovne sú dané vopred a stačí
    sa pozrieť, či ich sviečka pretla. Pri trailingu na tom ale všetko závisí: keď
    cena najprv vyletí hore, trailing sa posunie a stop môže padnúť ešte v tej istej
    sviečke; keď najprv klesne, stop je ešte na starej úrovni a obchod prežije.

    Reálny prípad (BTCUSDT 3m, 2026-08-28 16:51): sviečka mala open 79 250,0,
    high 79 490,6 a low 79 245,7. Low je od openu 4,3 bodu, high 240,6 — takže cena
    šla najprv dole a až potom hore, trailing sa aktivoval až na konci sviečky
    a obchod pokračoval. Bez tohto pravidla by sme ho zavreli o 4 minúty skôr
    a o 77,6 bodu nižšie než TradingView.
    """
    return (abs(bar_open - low) > abs(high - bar_open)) if long else (
        abs(high - bar_open) > abs(bar_open - low)
    )


@dataclass(frozen=True, slots=True)
class TrailingPlan:
    """Trailing parametre v cenových bodoch aj v tickoch.

    Obe jednotky sú tu zámerne: `strategy.exit()` v TradingView pracuje s **tickami**,
    takže ticky treba na porovnávanie s referenčným backtestom, zatiaľ čo Freqtrade aj
    MultiCharts pracujú s **cenovými bodmi**.

    (Pine mal navyše `trailFreqPct` pre PickMyTrade — to sa neportuje.)
    """

    activation_price_distance: float  # cenové body
    offset_price_distance: float  # cenové body
    activation_ticks: float
    offset_ticks: float

    def stop_price(
        self, direction: Direction, entry: float, base_stop: float, extreme: float
    ) -> float:
        """Efektívny stop po zohľadnení trailingu — Pine `strategy.exit(trail_points=, trail_offset=)`.

        `extreme` je najlepšia cena dosiahnutá od vstupu (najvyššie high pre LONG,
        najnižšie low pre SHORT).

        Kým zisk nedosiahne `trailActivationR`, platí pôvodný SL. Potom stop sleduje
        `extreme` vo vzdialenosti `trailOffsetR` a **nikdy sa nevracia späť** — preto
        `max`/`min` proti pôvodnému stopu.

        Pri `rrRatio <= trailActivationR` sa trailing nikdy neprejaví: TP je na rovnakej
        alebo bližšej úrovni než aktivácia, takže obchod skončí skôr. Preto sa táto
        vetva pri RR 1 (referenčný golden beh) vôbec nespustí a parita ostáva platná.
        """
        if direction is Direction.LONG:
            if extreme - entry < self.activation_price_distance:
                return base_stop
            return max(base_stop, extreme - self.offset_price_distance)
        if entry - extreme < self.activation_price_distance:
            return base_stop
        return min(base_stop, extreme + self.offset_price_distance)

    @classmethod
    def build(cls, cfg: IBSConfig, inst: InstrumentSpec, sl_distance: float) -> "TrailingPlan | None":
        if not cfg.enableTrailing or sl_distance <= 0 or inst.tick_size <= 0:
            return None
        activation = cfg.trailActivationR * sl_distance
        offset = cfg.trailOffsetR * sl_distance
        return cls(
            activation_price_distance=activation,
            offset_price_distance=offset,
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
