"""Kruhová história barov s Pine sémantikou indexovania.

V Pine je ``low[0]`` aktuálny bar, ``low[1]`` predchádzajúci atď. Stavový automat
sa na to spolieha na desiatkach miest (`imbLookback`, `slLookback`, gap hľadanie),
takže sa oplatí mať to na jednom mieste a rovnako.

Drží sa len toľko barov, koľko treba — bez toho by pri dlhom backteste rástla pamäť
zbytočne.
"""

from __future__ import annotations

from collections import deque

from .types import Bar

__all__ = ["BarHistory"]


class BarHistory:
    """Posledných N barov + priebežné SMA, ktoré Pine počíta cez `ta.sma`."""

    def __init__(self, maxlen: int = 400) -> None:
        self._bars: deque[Bar] = deque(maxlen=maxlen)
        #: Pine `bar_index` — rastie donekonečna, aj keď staré bary z pamäte vypadnú.
        self.bar_index = -1

    def append(self, bar: Bar) -> None:
        self._bars.append(bar)
        self.bar_index += 1

    def __len__(self) -> int:
        return len(self._bars)

    def __bool__(self) -> bool:
        return bool(self._bars)

    def __getitem__(self, offset: int) -> Bar:
        """Pine ``bar[offset]`` — 0 je aktuálny bar."""
        if offset < 0:
            raise IndexError("offset musí byť >= 0 (Pine indexuje dozadu)")
        if offset >= len(self._bars):
            raise IndexError(f"bar[{offset}] nie je v histórii ({len(self._bars)} barov)")
        return self._bars[-1 - offset]

    def has(self, offset: int) -> bool:
        return 0 <= offset < len(self._bars)

    @property
    def current(self) -> Bar:
        return self._bars[-1]

    def index_of(self, offset: int) -> int:
        """`bar_index` baru vzdialeného `offset` barov dozadu."""
        return self.bar_index - offset

    # -- kĺzavé priemery -------------------------------------------------- #

    def sma_volume(self, length: int, offset: int = 0) -> float:
        """Pine ``ta.sma(volume, length)[offset]``. Vráti 0.0, kým nie je dosť barov."""
        return self._sma(lambda b: b.volume, length, offset)

    def sma_range(self, length: int, offset: int = 0) -> float:
        """Pine ``ta.sma(high - low, length)[offset]``."""
        return self._sma(lambda b: b.high - b.low, length, offset)

    def _sma(self, pick, length: int, offset: int) -> float:
        if length <= 0 or len(self._bars) < length + offset:
            return 0.0
        total = 0.0
        for i in range(offset, offset + length):
            total += pick(self[i])
        return total / length
