"""Detektor divergencií — bar-by-bar port „Divergence for Many Indicators v4" (LonesomeTheBlue).

Pôvodná Freqtrade stratégia mala tento algoritmus prepísaný do pandas (`div_positive` /
`div_negative` nad `df.at[...]`) a pivoty brala z `argrelextrema` nad **celým** DataFrame —
teda pivot bol známy skôr, než ho `prd` barov vpravo potvrdilo (pohľad dopredu, ktorý
v backteste vyzerá ako edge). Tu sa pivot použije až po potvrdení (`ta.Pivots`), presne
ako Pine `ta.pivothigh`.

Definície (Pine originál, zachované do písmena):

* **regulárna býčia**: cena urobí nižšie low než pivot, indikátor vyššie low;
  **skrytá býčia**: cena vyššie low, indikátor nižšie low. Medvedie symetricky na pivotoch high.
* Divergencia platí len keď medzi pivotom a teraz **nič nepretne spojnicu** — ani indikátor,
  ani zatváracia cena („arrived").
* `dontConfirm = False` čaká na potvrdenie: hľadá sa až keď indikátor alebo close
  stúpli (pre býčiu) a porovnáva sa predchádzajúci bar (`startpoint = 1`).
* Pivot musí byť aspoň 6 barov starý (Pine `len > 5`) a najviac `maxBars`; skúša sa
  najviac `maxPp` posledných pivotov.

Výstup na bare je zoznam zásahov (indikátor, druh, dĺžka, pivot) zvlášť pre býčiu
a medvediu stranu; stratégia z toho potrebuje väčšinou len počty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from tradebot.core.types import Bar

from .ta import CCI, CDV, CMF, MACD, MFI, MOM, OBV, RSI, VWMACD, Pivots, Series, Stoch

__all__ = ["INDICATORS", "INDICATOR_TITLES", "DivHit", "DivHits", "DivergenceDetector"]

#: Kľúče indikátorov v poradí, v akom ich mala pôvodná stratégia (`DivInds`).
INDICATORS: tuple[str, ...] = (
    "macd", "macdh", "rsi", "stoch", "cci", "mom", "obv", "vwmacd", "cmf", "mfi", "cdv",
)

INDICATOR_TITLES: dict[str, str] = {
    "macd": "MACD", "macdh": "MACD hist.", "rsi": "RSI", "stoch": "Stoch", "cci": "CCI",
    "mom": "Momentum", "obv": "OBV", "vwmacd": "VW MACD", "cmf": "CMF", "mfi": "MFI",
    "cdv": "CDV",
}


@dataclass(frozen=True, slots=True)
class DivHit:
    indicator: str
    hidden: bool
    #: koľko barov dozadu je pivot
    length: int
    pivot_index: int
    pivot_price: float
    pivot_time: int


@dataclass(slots=True)
class DivHits:
    buy: list[DivHit] = field(default_factory=list)
    sell: list[DivHit] = field(default_factory=list)

    @property
    def buy_count(self) -> int:
        return len(self.buy)

    @property
    def sell_count(self) -> int:
        return len(self.sell)


class _Indicators:
    """Všetky indikátory nad jedným prúdom barov; hodnoty za bar ako dict kľúč -> float | None."""

    def __init__(self, keys: set[str], extra: dict[str, Callable[[Bar], float | None]] | None = None) -> None:
        self.keys = set(keys)
        self.extra = dict(extra or {})
        self._rsi = RSI(14)
        self._macd = MACD(12, 26, 9)
        self._stoch = Stoch(14, 3)
        self._cci = CCI(10)
        self._mom = MOM(10)
        self._obv = OBV()
        self._vwmacd = VWMACD(12, 26)
        self._cmf = CMF(21)
        self._mfi = MFI(14)
        self._cdv = CDV()

    def push(self, bar: Bar) -> dict[str, float | None]:
        out: dict[str, float | None] = {}
        k = self.keys
        if "rsi" in k:
            out["rsi"] = self._rsi.push(bar.close)
        if "macd" in k or "macdh" in k:
            macd, _sig, hist = self._macd.push(bar.close)
            if "macd" in k:
                out["macd"] = macd
            if "macdh" in k:
                out["macdh"] = hist
        if "stoch" in k:
            out["stoch"] = self._stoch.push(bar.high, bar.low, bar.close)
        if "cci" in k:
            out["cci"] = self._cci.push(bar.high, bar.low, bar.close)
        if "mom" in k:
            out["mom"] = self._mom.push(bar.close)
        if "obv" in k:
            out["obv"] = self._obv.push(bar.close, bar.volume)
        if "vwmacd" in k:
            out["vwmacd"] = self._vwmacd.push(bar.close, bar.volume)
        if "cmf" in k:
            out["cmf"] = self._cmf.push(bar.high, bar.low, bar.close, bar.volume)
        if "mfi" in k:
            out["mfi"] = self._mfi.push(bar.high, bar.low, bar.close, bar.volume)
        if "cdv" in k:
            out["cdv"] = self._cdv.push(bar)
        for name, fn in self.extra.items():
            out[name] = fn(bar)
        return out


class DivergenceDetector:
    """Jeden prúd barov (chart TF alebo HTF), jedna sada nastavení, zásahy na každom bare.

    `buy_inds` / `sell_inds` sú kľúče z `INDICATORS` (plus mená z `extra`), ktoré sa
    hľadajú pre býčiu resp. medvediu stranu — pôvodná stratégia ich mala prepínateľné
    zvlášť (`calc_<ind>_buy` / `calc_<ind>_sell`). `extra` sú vlastné indikátory
    (`meno -> f(bar)`), hlavne pre testy.
    """

    #: Pine `maxarraysize` — koľko posledných pivotov sa drží
    MAX_PIVOTS = 20

    def __init__(
        self,
        *,
        prd: int,
        source_close: bool,
        regular: bool,
        hidden: bool,
        max_pp: int,
        max_bars: int,
        dont_confirm: bool,
        buy_inds: set[str] | frozenset[str],
        sell_inds: set[str] | frozenset[str],
        extra: dict[str, Callable[[Bar], float | None]] | None = None,
    ) -> None:
        self.prd = int(prd)
        self.source_close = bool(source_close)
        self.regular = bool(regular)
        self.hidden = bool(hidden)
        self.max_pp = min(int(max_pp), self.MAX_PIVOTS)
        self.max_bars = int(max_bars)
        self.dont_confirm = bool(dont_confirm)
        self.buy_inds = tuple(k for k in (*INDICATORS, *(extra or {})) if k in buy_inds)
        self.sell_inds = tuple(k for k in (*INDICATORS, *(extra or {})) if k in sell_inds)
        keys = set(self.buy_inds) | set(self.sell_inds)
        self._ind = _Indicators(keys - set(extra or {}), extra)
        keep = self.max_bars + self.prd + 4
        self._close = Series(keep)
        self._high = Series(keep)
        self._low = Series(keep)
        self._src: dict[str, Series] = {k: Series(keep) for k in keys}
        self._pivots = Pivots(self.prd)
        #: najnovší prvý: (bar_index, hodnota, čas) — Pine `ph_positions` / `ph_vals`
        self.ph: list[tuple[int, float, int]] = []
        self.pl: list[tuple[int, float, int]] = []
        self.bar_index = -1

    # ------------------------------------------------------------------ #

    def on_bar(self, bar: Bar) -> DivHits:
        self.bar_index += 1
        values = self._ind.push(bar)
        self._close.push(bar.close)
        self._high.push(bar.high)
        self._low.push(bar.low)
        for k, s in self._src.items():
            s.push(values.get(k))

        hi_src = bar.close if self.source_close else bar.high
        lo_src = bar.close if self.source_close else bar.low
        ph, pl = self._pivots.push(hi_src, lo_src, bar.time)
        if ph is not None:
            self.ph.insert(0, ph)
            del self.ph[self.MAX_PIVOTS:]
        if pl is not None:
            self.pl.insert(0, pl)
            del self.pl[self.MAX_PIVOTS:]

        hits = DivHits()
        if self.bar_index < 1:
            return hits
        for name in self.buy_inds:
            hits.buy += self._side(name, bullish=True)
        for name in self.sell_inds:
            hits.sell += self._side(name, bullish=False)
        return hits

    # ------------------------------------------------------------------ #

    def _side(self, name: str, *, bullish: bool) -> list[DivHit]:
        """Regulárna a skrytá divergencia jedného indikátora na jednej strane."""
        src = self._src[name]
        s0, s1 = src[0], src[1]
        c0, c1 = self._close[0], self._close[1]
        if s0 is None or s1 is None or c0 is None or c1 is None:
            return []
        if bullish:
            go = self.dont_confirm or s0 > s1 or c0 > c1
        else:
            go = self.dont_confirm or s0 < s1 or c0 < c1
        if not go:
            return []
        startpoint = 0 if self.dont_confirm else 1
        out: list[DivHit] = []
        if self.regular:
            hit = self._search(name, src, bullish=bullish, hidden=False, startpoint=startpoint)
            if hit is not None:
                out.append(hit)
        if self.hidden:
            hit = self._search(name, src, bullish=bullish, hidden=True, startpoint=startpoint)
            if hit is not None:
                out.append(hit)
        return out

    def _search(self, name: str, src: Series, *, bullish: bool, hidden: bool, startpoint: int) -> DivHit | None:
        """Pine `positive_regular_positive_hidden_divergence` / `negative_…` — jedna vetva `cond`."""
        pivots = self.pl if bullish else self.ph
        if self.source_close:
            prsc = self._close
        else:
            prsc = self._low if bullish else self._high
        s0 = src[startpoint]
        p0 = prsc[startpoint]
        c0 = self._close[startpoint]
        if s0 is None or p0 is None or c0 is None:
            return None
        for x, (pos, val, when) in enumerate(pivots):
            if x >= self.max_pp:
                break
            length = self.bar_index - pos
            if length > self.max_bars:
                break
            if length <= 5:
                continue
            s_len = src[length]
            c_len = self._close[length]
            if s_len is None or c_len is None:
                continue
            if bullish:
                # regulárna: indikátor vyššie low, cena nižšie low; skrytá naopak
                ok = (s0 > s_len and p0 < val) if not hidden else (s0 < s_len and p0 > val)
            else:
                ok = (s0 < s_len and p0 > val) if not hidden else (s0 > s_len and p0 < val)
            if not ok:
                continue
            span = length - startpoint
            slope1 = (s0 - s_len) / span
            slope2 = (c0 - c_len) / span
            line1 = s0 - slope1
            line2 = c0 - slope2
            arrived = True
            for y in range(1 + startpoint, length):
                sy = src[y]
                cy = self._close[y] or 0.0
                if sy is None:
                    arrived = False
                    break
                if bullish:
                    if sy < line1 or cy < line2:
                        arrived = False
                        break
                elif sy > line1 or cy > line2:
                    arrived = False
                    break
                line1 -= slope1
                line2 -= slope2
            if arrived:
                return DivHit(name, hidden, length, pos, val, when)
        return None
