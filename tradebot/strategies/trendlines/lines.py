"""Trendovky na vlastnom TF: pivoty, výber platnej čiary a počítanie dotykov.

Čiara sa kreslí klasicky cez dva pivoty (`pivotLen` barov z oboch strán):

- **odpor** cez dva vrcholy (pri `classic` musí klesať — prerazenie nahor je long),
- **podpora** cez dve dná (pri `classic` musí rásť — prerazenie nadol je short).

Čiara je **platná**, keď ju medzi kotvami nepreráža žiadna sviečka (knôt alebo telo podľa
`anchorMode`, s toleranciou `touchTolAtr`) a za druhou kotvou ju nepreráža žiadne zatvorenie.
Z viacerých kandidátov sa berie ten s najviac dotykmi (pri zhode dlhší). Dotyk je pivot
blízko čiary alebo samostatná epizóda barov, ktoré sa k nej priblížili — tretí dotyk tak
môže prísť aj po vzniku čiary a čiara sa stane obchodovateľnou až vtedy (`minTouches`).

Vyšší TF sa skladá z barov grafu (`TFAggregator`, rovnaké pravidlo ako `core/candles.py`),
HTF bar je k dispozícii na prvom bare grafu novej periódy — nikdy sa nepoužije rozpracovaný.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from tradebot.core.types import Bar

from .config import AnchorMode, LineSlope, TrendlineConfig

__all__ = ["Line", "LineBook"]


@dataclass
class Line:
    """Trendovka: dve kotvy v čase (ms, open HTF baru) a cene."""

    kind: str          #: "res" (odpor, prerazenie nahor) alebo "sup" (podpora, prerazenie nadol)
    t1: int
    y1: float
    t2: int
    y2: float
    i1: int            #: index kotiev v baroch vlastného TF
    i2: int
    touches: int
    uid: int
    #: index posledného HTF baru, ktorý bol v dotyku (epizódy dotykov sa nepočítajú dvakrát)
    last_touch_i: int = -10
    consumed: bool = False
    drawn: bool = False

    @property
    def slope_ms(self) -> float:
        return (self.y2 - self.y1) / (self.t2 - self.t1) if self.t2 != self.t1 else 0.0

    def value(self, t_ms: int) -> float:
        return self.y1 + (t_ms - self.t1) * self.slope_ms


@dataclass
class _Pivot:
    i: int
    t: int
    price: float


@dataclass
class LineBook:
    """Stav trendoviek jedného TF; `on_htf_bar` volaj na každý uzavretý bar toho TF."""

    cfg: TrendlineConfig
    tf_ms: int
    bars: deque = field(default_factory=deque)
    count: int = 0
    atr: float = 0.0
    _tr_seed: list = field(default_factory=list)
    highs: list = field(default_factory=list)
    lows: list = field(default_factory=list)
    res: Line | None = None
    sup: Line | None = None
    _uid: int = 0
    #: čiary a pivoty, ktoré vznikli pri poslednom `on_htf_bar` (na kreslenie)
    new_lines: list = field(default_factory=list)
    new_pivots: list = field(default_factory=list)

    def __post_init__(self) -> None:
        cfg = self.cfg
        self.maxlen = int(cfg.lineMaxAgeBars) + 2 * int(cfg.pivotLen) + 20
        self.bars = deque(maxlen=self.maxlen)

    # ---- pomocné ---------------------------------------------------------- #

    def _hi(self, b: Bar) -> float:
        return b.high if self.cfg.anchorMode is AnchorMode.WICK else max(b.open, b.close)

    def _lo(self, b: Bar) -> float:
        return b.low if self.cfg.anchorMode is AnchorMode.WICK else min(b.open, b.close)

    def _bar(self, i: int) -> Bar | None:
        """HTF bar s indexom `i` (od začiatku), ak ešte je v okne."""
        k = i - (self.count - len(self.bars))
        return self.bars[k] if 0 <= k < len(self.bars) else None

    def _tol(self) -> float:
        return self.cfg.touchTolAtr.value * self.atr if self.atr > 0 else 0.0

    def _update_atr(self, b: Bar, prev: Bar | None) -> None:
        n = int(self.cfg.atrLen)
        tr = b.high - b.low if prev is None else max(b.high - b.low, abs(b.high - prev.close),
                                                     abs(b.low - prev.close))
        if self.atr > 0:
            self.atr += (tr - self.atr) / n
        else:
            self._tr_seed.append(tr)
            if len(self._tr_seed) >= n:
                self.atr = sum(self._tr_seed) / len(self._tr_seed)

    # ---- hlavný krok ------------------------------------------------------ #

    def on_htf_bar(self, b: Bar) -> None:
        self.new_lines = []
        self.new_pivots = []
        prev = self.bars[-1] if self.bars else None
        self.bars.append(b)
        self.count += 1
        self._update_atr(b, prev)
        i_now = self.count - 1

        # existujúce čiary: prerazenie zatvorením HTF, vek, nové dotyky
        tol = self._tol()
        for name in ("res", "sup"):
            ln: Line | None = getattr(self, name)
            if ln is None:
                continue
            v = ln.value(b.time)
            broken = b.close > v + 1e-12 if ln.kind == "res" else b.close < v - 1e-12
            if broken or ln.consumed or i_now - ln.i2 > self.cfg.lineMaxAgeBars:
                setattr(self, name, None)
                continue
            near = self._hi(b) >= v - tol if ln.kind == "res" else self._lo(b) <= v + tol
            if near and i_now > ln.i2 + 1:
                if i_now - ln.last_touch_i > 1:
                    ln.touches += 1
                ln.last_touch_i = i_now

        # nový pivot (potvrdený `pivotLen` barmi vpravo)
        L = int(self.cfg.pivotLen)
        if len(self.bars) >= 2 * L + 1 and self.atr > 0:
            c = self.bars[-L - 1]
            left = [self.bars[-L - 1 - k] for k in range(1, L + 1)]
            right = [self.bars[-k] for k in range(1, L + 1)]
            i_c = i_now - L
            ph = self._hi(c)
            if all(ph > self._hi(x) for x in left) and all(ph >= self._hi(x) for x in right):
                self._add_pivot(self.highs, _Pivot(i_c, c.time, ph), "res")
            pl = self._lo(c)
            if all(pl < self._lo(x) for x in left) and all(pl <= self._lo(x) for x in right):
                self._add_pivot(self.lows, _Pivot(i_c, c.time, pl), "sup")

    def _add_pivot(self, store: list, p: _Pivot, kind: str) -> None:
        store.append(p)
        if len(store) > int(self.cfg.maxPivots):
            del store[0]
        self.new_pivots.append((kind, p))
        line = self._best_line(store, kind)
        if line is not None:
            setattr(self, kind, line)
            self.new_lines.append(line)

    def _best_line(self, store: list, kind: str) -> Line | None:
        """Najlepšia platná čiara s najnovším pivotom ako druhou kotvou."""
        cfg = self.cfg
        b = store[-1]
        tol = self._tol()
        i_now = self.count - 1
        best: tuple[int, int, Line] | None = None
        for a in reversed(store[:-1]):
            gap = b.i - a.i
            if gap < cfg.minAnchorGap:
                continue
            if cfg.lineSlope is LineSlope.CLASSIC:
                if kind == "res" and not b.price < a.price:
                    continue
                if kind == "sup" and not b.price > a.price:
                    continue
            per_bar = abs(b.price - a.price) / gap
            if self.atr > 0:
                if per_bar / self.atr < cfg.minSlopeAtr:
                    continue
                if cfg.maxSlopeAtr > 0 and per_bar / self.atr > cfg.maxSlopeAtr:
                    continue
            if self._bar(a.i) is None:
                continue
            ln = Line(kind, a.t, a.price, b.t, b.price, a.i, b.i, 2, 0)
            ok, touches = True, 2
            last = -10
            for i in range(a.i + 1, i_now + 1):
                x = self._bar(i)
                if x is None:
                    ok = False
                    break
                v = ln.value(x.time)
                if i == b.i:
                    continue
                if i < b.i:
                    val = self._hi(x) if kind == "res" else self._lo(x)
                    if (kind == "res" and val > v + tol) or (kind == "sup" and val < v - tol):
                        ok = False
                        break
                elif (kind == "res" and x.close > v) or (kind == "sup" and x.close < v):
                    ok = False
                    break
                near = self._hi(x) >= v - tol if kind == "res" else self._lo(x) <= v + tol
                if near and abs(i - a.i) > 1 and abs(i - b.i) > 1:
                    if i - last > 1:
                        touches += 1
                    last = i
            if not ok:
                continue
            ln.touches, ln.last_touch_i = touches, last
            key = (touches, gap)
            if best is None or key > best[:2]:
                best = (touches, gap, ln)
        if best is None:
            return None
        self._uid += 1
        best[2].uid = self._uid
        return best[2]
