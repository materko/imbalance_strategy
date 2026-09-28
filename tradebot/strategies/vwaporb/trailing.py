"""Stop na VWAP — posúva sa s VWAP bar po bare, obchod končí dotykom VWAP.

Pri ``profit_only`` (TP na cross VWAP) platí len vtedy, keď je VWAP za vstupom v zisku a posledný
bar zavrel na správnej strane VWAP — dotyk je potom naozaj cross a výber zisku; inak pôvodný stop.
Bez podmienky na close by 15m aktualizácia, ktorá posunie VWAP do zisku nad cenu, ktorá už je pod
ním, vyplnila „stop" hneď na otvorení so stratou (MNQ 19. 3. 2026 15:30 UTC).

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
    """VWAP a close baru grafu v čase (čas = koniec baru, keď sú známe), v poradí barov."""

    __slots__ = ("times", "values", "closes")

    def __init__(self) -> None:
        self.times: list[int] = []
        self.values: list[float] = []
        self.closes: list[float] = []

    def add(self, known_ms: int, value: float, close: float | None = None) -> None:
        if self.times and known_ms <= self.times[-1]:
            if known_ms == self.times[-1]:
                self.values[-1] = value
                self.closes[-1] = close if close is not None else self.closes[-1]
            return
        self.times.append(known_ms)
        self.values.append(value)
        self.closes.append(close if close is not None else float("nan"))

    def _index(self, ts_ms: int | None) -> int:
        if not self.values:
            return -1
        if ts_ms is None:
            return len(self.values) - 1
        return bisect_right(self.times, ts_ms) - 1

    def at(self, ts_ms: int | None) -> float | None:
        """VWAP platný v ``ts_ms`` — posledná hodnota známa najneskôr v ``ts_ms``."""
        i = self._index(ts_ms)
        return self.values[i] if i >= 0 else None

    def close_at(self, ts_ms: int | None) -> float | None:
        """Close posledného baru uzavretého najneskôr v ``ts_ms``."""
        i = self._index(ts_ms)
        return self.closes[i] if i >= 0 and self.closes[i] == self.closes[i] else None


@dataclass(frozen=True, slots=True)
class VwapTrailing(TrailingPlan):
    """Stop = VWAP − rezerva (long), VWAP + rezerva (short).

    Platí, až keď cena od vstupu bola na správnej strane VWAP (long: najvyššie high nad VWAP) —
    inak by pri vstupe pod VWAP skočil stop nad cenu. Dovtedy (a pred prvou hodnotou) pôvodný stop.
    """

    series: VwapSeries = field(default_factory=VwapSeries, compare=False, repr=False)
    buffer: float = 0.0
    #: TP na cross VWAP: stop na VWAP len keď je VWAP za vstupom v zisku; inak pôvodný stop
    profit_only: bool = False

    @classmethod
    def following(cls, series: VwapSeries, buffer: float, profit_only: bool = False) -> "VwapTrailing":
        return cls(activation_price_distance=0.0, offset_price_distance=0.0,
                   activation_ticks=0.0, offset_ticks=0.0, series=series, buffer=buffer,
                   profit_only=profit_only)

    def stop_price(self, direction: Direction, entry: float, base_stop: float, extreme: float) -> float:
        return self.stop_price_at(None, direction, entry, base_stop, extreme)

    def stop_price_at(self, ts_ms: int | None, direction: Direction, entry: float, base_stop: float,
                      extreme: float) -> float:
        vwap = self.series.at(ts_ms)
        if vwap is None:
            return base_stop
        close = self.series.close_at(ts_ms) if self.profit_only else None
        if direction is Direction.LONG:
            level = vwap - self.buffer
            if extreme <= vwap:
                return base_stop
            if self.profit_only and (level <= entry or close is None or close <= vwap):
                return base_stop
            return level
        level = vwap + self.buffer
        if extreme >= vwap:
            return base_stop
        if self.profit_only and (level >= entry or close is None or close >= vwap):
            return base_stop
        return level

    def scaled(self, factor: float) -> "VwapTrailing":
        """Stop je úroveň na grafe (VWAP), nie násobok rizika — posunutý stop ho nemení."""
        return self
