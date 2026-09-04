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

    def __init__(self, maxlen: int = 400, atr_len: int = 14) -> None:
        self._bars: deque[Bar] = deque(maxlen=maxlen)
        #: Pine `bar_index` — rastie donekonečna, aj keď staré bary z pamäte vypadnú.
        self.bar_index = -1
        self._atr_len = max(1, int(atr_len))
        self._atr = 0.0
        self._tr_sum = 0.0

    def append(self, bar: Bar) -> None:
        prev_close = self._bars[-1].close if self._bars else None
        self._bars.append(bar)
        self.bar_index += 1
        self._update_atr(bar, prev_close)

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

    # -- ATR ---------------------------------------------------------------- #

    @property
    def atr(self) -> float:
        """Wilderov ATR (Pine ``ta.atr(atrLen)``). 0.0, kým nie je dosť barov.

        Pine skript ATR nepoužíva — slúži výhradne na prepočet parametrov zadaných
        v jednotke ``atr`` (SizeSpec). Vďaka tomu sa dajú prahy naladené v bodoch na
        MNQ preniesť na inštrument s úplne inou cenovou škálou (ARCHITECTURE_port.md §3b).
        Referenčné ``_tv`` profily ho nepoužívajú — tie majú všetko v ``abs``/``ticks``.
        """
        return self._atr

    def _update_atr(self, bar: Bar, prev_close: float | None) -> None:
        tr = bar.high - bar.low
        if prev_close is not None:
            tr = max(tr, abs(bar.high - prev_close), abs(bar.low - prev_close))

        n = self._atr_len
        if self.bar_index < n:
            # Prvá hodnota je jednoduchý priemer prvých n true range - rovnako ako Pine RMA.
            self._tr_sum += tr
            self._atr = self._tr_sum / n if self.bar_index == n - 1 else 0.0
            return
        self._atr = (self._atr * (n - 1) + tr) / n

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
