"""Inkrementálne indikátory pre divergenčnú stratégiu — bar po bare, bez pandas.

Pôvodná Freqtrade stratégia počítala všetko vektorovo cez talib / qtpylib nad celým
DataFrame. Engine TradeBotu dostáva bary po jednom a musí bežať rovnako vo Freqtrade,
v MultiCharts aj v emulátore, takže každý indikátor tu má stav a metódu `push`.

Čo sa oproti knižničným verziám líši (vedome, drobnosti v rozbehu):

* EMA a Wilderov RMA sa rozbiehajú z jednoduchého priemeru prvých `n` hodnôt (ako talib),
  nie z prvej hodnoty (ako Pine `ta.ema`). Po ~3n baroch je rozdiel zanedbateľný.
* Heikin Ashi je štandardná (`ha_high = max(high, ha_open, ha_close)`); qtpylib, ktoré
  pôvodná stratégia použila, berie do `ha_high` surové `open`/`close`. Štandard je to,
  čo kreslí TradingView aj MultiCharts.
* Supertrend je Pine `ta.supertrend` (otočenie proti **predchádzajúcemu** finálnemu pásmu);
  pôvodný ručný výpočet porovnával s aktuálnym pásmom a ATR mal `ewm(com=n)`.

Indikátor vráti `None`, kým nemá dosť barov — detektor divergencií to berie ako
„hodnota nie je" a takú dvojicu pivotov jednoducho preskočí.
"""

from __future__ import annotations

from collections import deque

from tradebot.core.types import Bar

__all__ = [
    "Series", "HeikinAshi", "SMA", "EMA", "RMA", "RSI", "MACD", "Stoch", "CCI", "MOM",
    "OBV", "VWMACD", "CMF", "MFI", "CDV", "Supertrend", "Pivots",
]


class Series:
    """História hodnôt s Pine indexovaním: `s[0]` je aktuálna hodnota, `s[k]` k barov dozadu.

    Drží sa len `keep` hodnôt (list sa oreže, keď narastie na dvojnásobok), takže
    päťročný beh nerastie v pamäti. Chýbajúca hodnota je `None`.
    """

    __slots__ = ("_v", "keep")

    def __init__(self, keep: int) -> None:
        self.keep = max(2, int(keep))
        self._v: list = []

    def push(self, value) -> None:
        self._v.append(value)
        if len(self._v) > 2 * self.keep:
            del self._v[: len(self._v) - self.keep]

    def __getitem__(self, k: int):
        """`None`, keď toľko histórie ešte nie je."""
        if k < 0 or k >= len(self._v):
            return None
        return self._v[-1 - k]

    def __len__(self) -> int:
        return len(self._v)


class HeikinAshi:
    """Bar → Heikin Ashi bar. Objem ostáva skutočný (indikátory objemu ho potrebujú)."""

    __slots__ = ("_open", "_close")

    def __init__(self) -> None:
        self._open: float | None = None
        self._close: float | None = None

    def push(self, bar: Bar) -> Bar:
        ha_close = (bar.open + bar.high + bar.low + bar.close) / 4.0
        if self._open is None:
            ha_open = (bar.open + bar.close) / 2.0
        else:
            ha_open = (self._open + self._close) / 2.0
        ha_high = max(bar.high, ha_open, ha_close)
        ha_low = min(bar.low, ha_open, ha_close)
        self._open, self._close = ha_open, ha_close
        return Bar(time=bar.time, open=ha_open, high=ha_high, low=ha_low, close=ha_close, volume=bar.volume)


class SMA:
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


class EMA(_Smooth):
    def __init__(self, n: int) -> None:
        super().__init__(n, 2.0 / (int(n) + 1))


class RMA(_Smooth):
    """Wilderov kĺzavý priemer (Pine `ta.rma`, základ ATR aj RSI)."""

    def __init__(self, n: int) -> None:
        super().__init__(n, 1.0 / int(n))


class RSI:
    __slots__ = ("_up", "_dn", "_prev", "value")

    def __init__(self, n: int = 14) -> None:
        self._up, self._dn = RMA(n), RMA(n)
        self._prev: float | None = None
        self.value: float | None = None

    def push(self, close: float) -> float | None:
        if self._prev is None:
            self._prev = close
            return None
        change = close - self._prev
        self._prev = close
        up = self._up.push(max(change, 0.0))
        dn = self._dn.push(max(-change, 0.0))
        if up is None or dn is None:
            return None
        self.value = 100.0 if dn == 0 else 100.0 - 100.0 / (1.0 + up / dn)
        return self.value


class MACD:
    """(macd, signál, histogram) — alebo `(None, None, None)`, kým sa nerozbehne."""

    __slots__ = ("_fast", "_slow", "_sig")

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self._fast, self._slow, self._sig = EMA(fast), EMA(slow), EMA(signal)

    def push(self, close: float) -> tuple[float | None, float | None, float | None]:
        f = self._fast.push(close)
        s = self._slow.push(close)
        if f is None or s is None:
            return None, None, None
        macd = f - s
        sig = self._sig.push(macd)
        if sig is None:
            return macd, None, None
        return macd, sig, macd - sig


class Stoch:
    """Pomalé %K: SMA(`smooth`) z rýchleho %K nad `n` barmi (pôvodné `slow_k`)."""

    __slots__ = ("n", "_h", "_l", "_sma")

    def __init__(self, n: int = 14, smooth: int = 3) -> None:
        self.n = int(n)
        self._h: deque = deque(maxlen=self.n)
        self._l: deque = deque(maxlen=self.n)
        self._sma = SMA(smooth)

    def push(self, high: float, low: float, close: float) -> float | None:
        self._h.append(high)
        self._l.append(low)
        if len(self._h) < self.n:
            return None
        hi, lo = max(self._h), min(self._l)
        fast_k = 50.0 if hi == lo else 100.0 * (close - lo) / (hi - lo)
        return self._sma.push(fast_k)


class CCI:
    __slots__ = ("n", "_tp")

    def __init__(self, n: int = 10) -> None:
        self.n = int(n)
        self._tp: deque = deque(maxlen=self.n)

    def push(self, high: float, low: float, close: float) -> float | None:
        tp = (high + low + close) / 3.0
        self._tp.append(tp)
        if len(self._tp) < self.n:
            return None
        mean = sum(self._tp) / self.n
        dev = sum(abs(x - mean) for x in self._tp) / self.n
        return 0.0 if dev == 0 else (tp - mean) / (0.015 * dev)


class MOM:
    __slots__ = ("n", "_q")

    def __init__(self, n: int = 10) -> None:
        self.n = int(n)
        self._q: deque = deque(maxlen=self.n + 1)

    def push(self, close: float) -> float | None:
        self._q.append(close)
        if len(self._q) <= self.n:
            return None
        return close - self._q[0]


class OBV:
    __slots__ = ("_prev", "value")

    def __init__(self) -> None:
        self._prev: float | None = None
        self.value = 0.0

    def push(self, close: float, volume: float) -> float:
        if self._prev is not None:
            if close > self._prev:
                self.value += volume
            elif close < self._prev:
                self.value -= volume
        self._prev = close
        return self.value


class VWMACD:
    """Objemovo vážený MACD: VWMA(12) − VWMA(26) (pôvodný `vwmacd`)."""

    __slots__ = ("_pf", "_vf", "_ps", "_vs")

    def __init__(self, fast: int = 12, slow: int = 26) -> None:
        self._pf, self._vf, self._ps, self._vs = SMA(fast), SMA(fast), SMA(slow), SMA(slow)

    def push(self, close: float, volume: float) -> float | None:
        pf, vf = self._pf.push(close * volume), self._vf.push(volume)
        ps, vs = self._ps.push(close * volume), self._vs.push(volume)
        if pf is None or ps is None or not vf or not vs:
            return None
        return pf / vf - ps / vs


class CMF:
    """Chaikin Money Flow (`technical.indicators.chaikin_money_flow`, 21)."""

    __slots__ = ("_mfv", "_vol")

    def __init__(self, n: int = 21) -> None:
        self._mfv, self._vol = SMA(n), SMA(n)

    def push(self, high: float, low: float, close: float, volume: float) -> float | None:
        rng = high - low
        mfm = 0.0 if rng == 0 else ((close - low) - (high - close)) / rng
        mfv = self._mfv.push(mfm * volume)
        vol = self._vol.push(volume)
        if mfv is None or not vol:
            return None
        return mfv / vol


class MFI:
    __slots__ = ("n", "_pos", "_neg", "_prev_tp")

    def __init__(self, n: int = 14) -> None:
        self.n = int(n)
        self._pos: deque = deque(maxlen=self.n)
        self._neg: deque = deque(maxlen=self.n)
        self._prev_tp: float | None = None

    def push(self, high: float, low: float, close: float, volume: float) -> float | None:
        tp = (high + low + close) / 3.0
        if self._prev_tp is None:
            self._prev_tp = tp
            return None
        flow = tp * volume
        self._pos.append(flow if tp > self._prev_tp else 0.0)
        self._neg.append(flow if tp < self._prev_tp else 0.0)
        self._prev_tp = tp
        if len(self._pos) < self.n:
            return None
        pos, neg = sum(self._pos), sum(self._neg)
        if neg == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + pos / neg)


class CDV:
    """Kumulatívna delta objemu z knôtov sviečky, nulovaná o polnoci UTC (pôvodné `calc_cdv`).

    Pôvodný výpočet delil vzdialenosti tickom — ten sa ale v pomere krátí, takže tu
    ide priamo v cene a inštrument netreba.
    """

    __slots__ = ("_day", "value")

    def __init__(self) -> None:
        self._day: int | None = None
        self.value = 0.0

    def push(self, bar: Bar) -> float:
        rng = bar.high - bar.low
        if bar.open > bar.close:
            top, bottom = bar.high - bar.open, bar.close - bar.low
            ticks_up, ticks_down = top + bottom, rng
        else:
            top, bottom = bar.high - bar.close, bar.open - bar.low
            ticks_up, ticks_down = rng, top + bottom
        total = ticks_up + ticks_down
        per_unit = 0.0 if total == 0 else bar.volume / total
        delta = ticks_up * per_unit - ticks_down * per_unit
        day = bar.time // 86_400_000
        if self._day is None or day != self._day:
            self.value = delta
            self._day = day
        else:
            self.value += delta
        return self.value


class Supertrend:
    """Pine `ta.supertrend(mult, len)` nad barmi, ktoré dostane (tu Heikin Ashi).

    `trend` je +1 (cena nad čiarou), −1 (pod ňou) alebo `None`, kým ATR nie je; `line`
    je hodnota supertrendu na poslednom bare.
    """

    __slots__ = ("mult", "_atr", "_prev_close", "_up", "_dn", "trend", "line")

    def __init__(self, length: int = 15, mult: float = 4.0) -> None:
        self.mult = float(mult)
        self._atr = RMA(length)
        self._prev_close: float | None = None
        self._up: float | None = None  # spodné pásmo (podpora v uptrende)
        self._dn: float | None = None  # horné pásmo
        self.trend: int | None = None
        self.line: float | None = None

    def push(self, bar: Bar) -> int | None:
        tr = bar.high - bar.low
        if self._prev_close is not None:
            tr = max(tr, abs(bar.high - self._prev_close), abs(bar.low - self._prev_close))
        atr = self._atr.push(tr)
        prev_close, prev_up, prev_dn = self._prev_close, self._up, self._dn
        self._prev_close = bar.close
        if atr is None:
            return None
        hl2 = (bar.high + bar.low) / 2.0
        up = hl2 - self.mult * atr
        dn = hl2 + self.mult * atr
        if prev_up is not None and prev_close is not None and prev_close > prev_up:
            up = max(up, prev_up)
        if prev_dn is not None and prev_close is not None and prev_close < prev_dn:
            dn = min(dn, prev_dn)
        if self.trend is None:
            self.trend = 1
        elif self.trend == -1 and prev_dn is not None and bar.close > prev_dn:
            self.trend = 1
        elif self.trend == 1 and prev_up is not None and bar.close < prev_up:
            self.trend = -1
        self._up, self._dn = up, dn
        self.line = up if self.trend == 1 else dn
        return self.trend


class Pivots:
    """Pine `ta.pivothigh(src, prd, prd)` / `ta.pivotlow` — pivot sa potvrdí až `prd` barov
    po tom, čo nastal, a hlási sa s indexom a časom toho **pôvodného** baru.

    Prísne `>` resp. `<` na oboch stranách (ako `argrelextrema` v pôvodnej stratégii):
    plató rovnakých hodnôt pivot nie je.
    """

    __slots__ = ("prd", "_h", "_l", "_t", "_idx")

    def __init__(self, prd: int) -> None:
        self.prd = max(1, int(prd))
        n = 2 * self.prd + 1
        self._h: deque = deque(maxlen=n)
        self._l: deque = deque(maxlen=n)
        self._t: deque = deque(maxlen=n)
        self._idx = -1

    def push(self, high_src: float, low_src: float, time_ms: int) -> tuple[tuple[int, float, int] | None, tuple[int, float, int] | None]:
        """Vráti `(pivot_high, pivot_low)`; každý je `(bar_index, hodnota, čas)` alebo `None`."""
        self._idx += 1
        self._h.append(high_src)
        self._l.append(low_src)
        self._t.append(time_ms)
        n = 2 * self.prd + 1
        if len(self._h) < n:
            return None, None
        mid = self.prd
        ph = pl = None
        hv, lv = self._h[mid], self._l[mid]
        if all(self._h[i] < hv for i in range(n) if i != mid):
            ph = (self._idx - self.prd, hv, self._t[mid])
        if all(self._l[i] > lv for i in range(n) if i != mid):
            pl = (self._idx - self.prd, lv, self._t[mid])
        return ph, pl
