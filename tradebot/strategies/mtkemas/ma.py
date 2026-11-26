"""Kĺzavé priemery MTK EMAS bar po bare — tie isté vzorce ako štúdia Mac mini (iCloud KLZAKY-STUDIA, `study2.ma`).

Každý priemer dostáva zavretie (a objem) jedného baru a vráti hodnotu alebo `None`, kým nemá dosť barov.
EMA / RMA / DEMA / TEMA = pandas `ewm(adjust=False)` (štart prvou hodnotou), SMA / WMA / VWMA = kĺzavé okno,
HMA = WMA(2·WMA(n/2) − WMA(n), √n), KAMA = Kaufman (ER perióda n, rýchla 2, pomalá 30). Súčty sú obyčajné
sčítanie zľava (rovnaké v C# `MtkEmasMa.cs`), aby Python a C# dali tie isté bity.
"""

from __future__ import annotations

import math
from collections import deque

__all__ = ["make_ma", "Atr", "MA_KINDS"]

MA_KINDS = ("ema", "sma", "wma", "hma", "dema", "tema", "rma", "vwma", "kama")


def _sum(xs) -> float:
    t = 0.0
    for x in xs:
        t += x
    return t


class _Ewm:
    """pandas `ewm(alpha, adjust=False)`: y = (1 − a)·y + a·x, štart prvou hodnotou."""

    def __init__(self, alpha: float) -> None:
        self.a = alpha
        self.y: float | None = None

    def push(self, x: float) -> float:
        self.y = x if self.y is None else (1.0 - self.a) * self.y + self.a * x
        return self.y


class _Ema:
    def __init__(self, n: int, rma: bool = False) -> None:
        self.n = n
        self.e = _Ewm(1.0 / n if rma else 2.0 / (n + 1))
        self.count = 0

    def push(self, c: float, v: float) -> float | None:
        self.count += 1
        y = self.e.push(c)
        return y if self.count >= self.n else None


class _Sma:
    def __init__(self, n: int) -> None:
        self.n = n
        self.w: deque[float] = deque(maxlen=n)

    def push(self, c: float, v: float) -> float | None:
        self.w.append(c)
        return _sum(self.w) / self.n if len(self.w) == self.n else None


class _Wma:
    def __init__(self, n: int) -> None:
        self.n = n
        self.w: deque[float] = deque(maxlen=n)
        self.den = n * (n + 1) / 2

    def push(self, c: float, v: float = 0.0) -> float | None:
        self.w.append(c)
        if len(self.w) < self.n:
            return None
        t = 0.0
        for i, x in enumerate(self.w):
            t += (i + 1) * x
        return t / self.den


class _Hma:
    def __init__(self, n: int) -> None:
        self.half = _Wma(max(1, n // 2))
        self.full = _Wma(n)
        self.out = _Wma(max(1, int(round(math.sqrt(n)))))

    def push(self, c: float, v: float) -> float | None:
        a = self.half.push(c)
        b = self.full.push(c)
        if a is None or b is None:
            return None
        return self.out.push(2 * a - b)


class _Dema:
    def __init__(self, n: int, triple: bool = False) -> None:
        a = 2.0 / (n + 1)
        self.e1, self.e2, self.e3 = _Ewm(a), _Ewm(a), _Ewm(a)
        self.triple = triple
        self.skip = (3 if triple else 2) * n
        self.count = 0

    def push(self, c: float, v: float) -> float | None:
        self.count += 1
        y1 = self.e1.push(c)
        y2 = self.e2.push(y1)
        if self.triple:
            r = 3 * y1 - 3 * y2 + self.e3.push(y2)
        else:
            r = 2 * y1 - y2
        return r if self.count > self.skip else None


class _Vwma:
    def __init__(self, n: int) -> None:
        self.n = n
        self.cv: deque[float] = deque(maxlen=n)
        self.vv: deque[float] = deque(maxlen=n)

    def push(self, c: float, v: float) -> float | None:
        self.cv.append(c * v)
        self.vv.append(v)
        if len(self.vv) < self.n:
            return None
        den = _sum(self.vv)
        return _sum(self.cv) / den if den != 0 else None


class _Kama:
    _FAST = 2.0 / 3.0
    _SLOW = 2.0 / 31.0

    def __init__(self, n: int) -> None:
        self.n = n
        self.closes: deque[float] = deque(maxlen=n + 1)
        self.diffs: deque[float] = deque(maxlen=n)
        self.prev: float | None = None
        self.val: float | None = None

    def push(self, c: float, v: float) -> float | None:
        self.diffs.append(0.0 if self.prev is None else abs(c - self.prev))
        self.prev = c
        self.closes.append(c)
        if len(self.closes) < self.n + 1:
            return None
        if self.val is None:
            self.val = c                     # prvá hodnota na indexe n = zavretie
            return self.val
        ch = abs(c - self.closes[0])
        vol = _sum(self.diffs)
        er = ch / vol if vol > 0 else 0.0
        k = er * (self._FAST - self._SLOW) + self._SLOW
        self.val = self.val + k * k * (c - self.val)
        return self.val


def make_ma(kind: str, n: int):
    n = max(1, int(n))
    kind = str(kind)
    if kind == "ema":
        return _Ema(n)
    if kind == "rma":
        return _Ema(n, rma=True)
    if kind == "sma":
        return _Sma(n)
    if kind == "wma":
        return _Wma(n)
    if kind == "hma":
        return _Hma(n)
    if kind == "dema":
        return _Dema(n)
    if kind == "tema":
        return _Dema(n, triple=True)
    if kind == "vwma":
        return _Vwma(n)
    if kind == "kama":
        return _Kama(n)
    raise ValueError(f"neznámy typ priemeru {kind!r}")


class Atr:
    """ATR = RMA(true range, n), štart prvým TR (ako štúdia: pandas `ewm(alpha=1/n, adjust=False)`)."""

    def __init__(self, n: int) -> None:
        self.e = _Ewm(1.0 / max(1, int(n)))
        self.prev_close: float | None = None
        self.value = 0.0

    def push(self, high: float, low: float, close: float) -> float:
        pc = close if self.prev_close is None else self.prev_close
        tr = max(high - low, max(abs(high - pc), abs(low - pc)))
        self.prev_close = close
        self.value = self.e.push(tr)
        return self.value
