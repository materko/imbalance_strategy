"""Kĺzavé priemery bar po bare — SMA, EMA a Wilderov RMA.

Engine TradeBotu dostáva bary po jednom a musí bežať rovnako vo Freqtrade, v MultiCharts
aj v emulátore, takže indikátor tu má stav a metódu ``push``, nie vektorový výpočet nad
DataFrame. Sú v jadre, lebo ich potrebuje viac stratégií a dve implementácie toho istého
priemeru by znamenali dve rôzne čísla z tých istých dát.

Rozbeh: EMA aj RMA sa rozbiehajú z jednoduchého priemeru prvých ``n`` hodnôt (ako talib),
nie z prvej hodnoty (ako Pine ``ta.ema``). Po ~3n baroch je rozdiel zanedbateľný; koľko
barov to presne je, hovorí ``tradebot.core.warmup.ema_bars`` / ``rma_bars``.

Kým indikátor nemá dosť barov, vracia ``None`` — volajúci sa má rozhodnúť, čo s tým
(filter typicky neprepustí obchod, kresba jednoducho začne neskôr).
"""

from __future__ import annotations

from collections import deque

from .warmup import decay_bars

__all__ = ["SMA", "EMA", "RMA"]


class SMA:
    """Jednoduchý kĺzavý priemer posledných ``n`` hodnôt."""

    __slots__ = ("n", "_q", "_sum")

    def __init__(self, n: int) -> None:
        self.n = max(1, int(n))
        self._q: deque = deque(maxlen=self.n)
        self._sum = 0.0

    def push(self, v: float) -> float | None:
        if len(self._q) == self.n:
            self._sum -= self._q[0]
        self._q.append(v)
        self._sum += v
        return self._sum / self.n if len(self._q) == self.n else None

    @property
    def value(self) -> float | None:
        return self._sum / self.n if len(self._q) == self.n else None

    @property
    def warmup_bars(self) -> int:
        return self.n


class _Smooth:
    """Spoločný základ EMA/RMA: rozbeh z SMA prvých `n` hodnôt, potom rekurzia."""

    __slots__ = ("n", "alpha", "value", "_seed")

    def __init__(self, n: int, alpha: float) -> None:
        self.n = max(1, int(n))
        self.alpha = alpha
        self.value: float | None = None
        self._seed = SMA(self.n)

    def push(self, v: float) -> float | None:
        if self.value is None:
            seed = self._seed.push(v)
            if seed is not None:
                self.value = seed
            return self.value
        self.value = self.value + self.alpha * (v - self.value)
        return self.value

    @property
    def warmup_bars(self) -> int:
        """SMA štart + dozvuk štartovacej hodnoty — `tradebot.core.warmup`."""
        return self.n + decay_bars(self.alpha)


class EMA(_Smooth):
    """Exponenciálny kĺzavý priemer, `alpha = 2/(n+1)`."""

    def __init__(self, n: int) -> None:
        super().__init__(n, 2.0 / (int(n) + 1))


class RMA(_Smooth):
    """Wilderov kĺzavý priemer (Pine `ta.rma`, základ ATR aj RSI), `alpha = 1/n`."""

    def __init__(self, n: int) -> None:
        super().__init__(n, 1.0 / int(n))
