"""Stop na VWAP — posúva sa s VWAP bar po bare, obchod končí dotykom VWAP.

Hodnota stopu závisí od času: počas sviečky, ktorá začína v ``ts``, platí VWAP známy v tom
čase (posledný uzavretý pred ``ts``). Engine hodnoty zapisuje do spoločnej série a adaptéry
sa pýtajú cez `TrailingPlan.stop_price_at` s časom sviečky, ktorú testujú — vo Freqtrade
backteste teda platí VWAP z času sviečky, nie posledný spočítaný.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

from tradebot.core.risk import TrailingPlan
from tradebot.core.types import Direction

__all__ = ["VwapSeries", "VwapTrailing"]


class VwapSeries:
    """Časy a hodnoty VWAP v poradí, ako ich engine spočítal (čas = koniec baru, keď je známa)."""

    __slots__ = ("times", "values")

    def __init__(self) -> None:
        self.times: list[int] = []
        self.values: list[float] = []

    def add(self, known_ms: int, value: float) -> None:
        if self.times and known_ms <= self.times[-1]:
            self.values[-1] = value if known_ms == self.times[-1] else self.values[-1]
            return
        self.times.append(known_ms)
        self.values.append(value)

    def at(self, ts_ms: int | None) -> float | None:
        """VWAP platný v ``ts_ms`` — posledná hodnota známa najneskôr v ``ts_ms``."""
        if not self.values:
            return None
        if ts_ms is None:
            return self.values[-1]
        i = bisect_right(self.times, ts_ms) - 1
        return self.values[i] if i >= 0 else None


@dataclass(frozen=True, slots=True)
class VwapTrailing(TrailingPlan):
    """Stop = VWAP − rezerva (long), VWAP + rezerva (short).

    Platí, až keď cena od vstupu bola na správnej strane VWAP (long: najvyššie high nad VWAP) —
    inak by pri vstupe pod VWAP skočil stop nad cenu. Dovtedy (a pred prvou hodnotou) pôvodný stop.
    """

    series: VwapSeries = field(default_factory=VwapSeries, compare=False, repr=False)
    buffer: float = 0.0

    @classmethod
    def following(cls, series: VwapSeries, buffer: float) -> "VwapTrailing":
        return cls(activation_price_distance=0.0, offset_price_distance=0.0,
                   activation_ticks=0.0, offset_ticks=0.0, series=series, buffer=buffer)

    def stop_price(self, direction: Direction, entry: float, base_stop: float, extreme: float) -> float:
        return self.stop_price_at(None, direction, entry, base_stop, extreme)

    def stop_price_at(self, ts_ms: int | None, direction: Direction, entry: float, base_stop: float,
                      extreme: float) -> float:
        vwap = self.series.at(ts_ms)
        if vwap is None:
            return base_stop
        if direction is Direction.LONG:
            return vwap - self.buffer if extreme > vwap else base_stop
        return vwap + self.buffer if extreme < vwap else base_stop

    def scaled(self, factor: float) -> "VwapTrailing":
        """Stop je úroveň na grafe (VWAP), nie násobok rizika — posunutý stop ho nemení."""
        return self
