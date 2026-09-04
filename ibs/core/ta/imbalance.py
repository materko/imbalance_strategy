"""Hľadanie imbalance (gapu) vnútri SD zóny — jadro IMB entry modelu.

Replika Pine riadkov 1637–1665 (STATE 0) a 1712–1739 (re-entry). Obe miesta
robia to isté, len sa inak zachovajú s výsledkom, takže je to tu raz.

Trojica sviečok `[lb]`, `[lb+1]`, `[lb+2]` tvorí gap, keď sa krajné dve neprekrývajú.
Prostredná (`lb+1`) je tá, ktorá nás zaujíma — z nej vychádza vstupná cena aj box.

Zámerná zvláštnosť, ktorú treba zachovať: pri zóne typu **LONG** sa hľadá
**bearish** gap (a naopak). Zóna je totiž miesto, kde sa cena má otočiť — gap
proti smeru zóny je ten, ktorý sa má vyplniť.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import IBSConfig
from ..history import BarHistory
from ..types import Direction, InstrumentSpec

__all__ = ["ImbalanceHit", "find_imbalance"]


@dataclass(frozen=True, slots=True)
class ImbalanceHit:
    """Nájdený gap. `offset` je Pine `midIdx` = `lb + 1`."""

    offset: int
    bar_index: int
    body_top: float
    body_bot: float
    open: float
    high: float
    low: float
    distance: float

    @property
    def entry_price(self) -> float:
        """Pine `zImbOpenA` — vstup je na OTVÁRACEJ cene prostrednej sviečky."""
        return self.open


def find_imbalance(
    history: BarHistory,
    zone_top: float,
    zone_bot: float,
    direction: Direction,
    cfg: IBSConfig,
    inst: InstrumentSpec,
    *,
    zone_created_bar_index: int,
    atr: float = 0.0,
) -> ImbalanceHit | None:
    """Vráti gap, ktorý je zóne **najbližšie**, alebo `None`.

    Prehľadáva `imbLookback` pozícií dozadu. Kandidát musí:
      * byť skutočný gap ≥ `minImbSizePoints`,
      * mať prostrednú sviečku nad zónou (pre LONG) / pod zónou (pre SHORT),
        alebo cez ňu celú prechádzať,
      * byť od zóny vzdialený najviac `imbMaxDistTicks`,
      * ležať až za vznikom zóny (Pine ``bar_index - (lb + 2) >= zCreatedBi``).
    """
    price = history.current.close
    min_imb = cfg.minImbSizePoints.resolve(inst, price=price, atr=atr)
    max_dist = cfg.imbMaxDistTicks.resolve(inst, price=price, atr=atr)

    best: ImbalanceHit | None = None

    for lb in range(cfg.imbLookback):
        if not history.has(lb + 2):
            continue
        if history.index_of(lb + 2) < zone_created_bar_index:
            continue

        near = history[lb]
        mid = history[lb + 1]
        far = history[lb + 2]

        is_bull_imb = (
            near.low > far.high
            and mid.close > far.high
            and (near.low - far.high) >= min_imb
        )
        is_bear_imb = (
            near.high < far.low
            and mid.close < far.low
            and (far.low - near.high) >= min_imb
        )

        if direction is Direction.LONG:
            # LONG zona hlada BEARISH gap - ten sa ma vyplnit smerom nahor.
            if not is_bear_imb:
                continue
            above = mid.open > zone_top
            through = mid.high >= zone_top and mid.low <= zone_bot
            if not (above or through):
                continue
            distance = max(0.0, mid.low - zone_top)
        else:
            if not is_bull_imb:
                continue
            below = mid.open < zone_bot
            through = mid.high >= zone_top and mid.low <= zone_bot
            if not (below or through):
                continue
            distance = max(0.0, zone_bot - mid.high)

        if distance > max_dist:
            continue
        if best is not None and distance >= best.distance:
            continue

        best = ImbalanceHit(
            offset=lb + 1,
            bar_index=history.index_of(lb + 1),
            body_top=mid.body_top,
            body_bot=mid.body_bottom,
            open=mid.open,
            high=mid.high,
            low=mid.low,
            distance=distance,
        )

    return best
