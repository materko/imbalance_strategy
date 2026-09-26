"""Trendovky na vlastnom TF: pivoty, výber platnej čiary a počítanie dotykov.

Čiara sa kreslí klasicky cez dva pivoty (`pivotLen` barov z oboch strán):

- **odpor** cez dva vrcholy (pri `classic` musí klesať — prerazenie nahor je long),
- **podpora** cez dve dná (pri `classic` musí rásť — prerazenie nadol je short).

Prvá kotva je začiatok trendu (najvyšší vrchol / najnižšie dno spomedzi `maxPivots` posledných
pivotov), druhá najnovší pivot; pivot, ktorý už bol kotvou, sa znova nepoužije (z jedného bodu
vedie najviac jedna čiara). Čiara je **platná**, keď ju medzi kotvami ani za druhou kotvou
nepreráža žiadna sviečka (knôt alebo telo podľa `anchorMode`, s toleranciou `touchTolAtr`).
Na každú stranu žije najviac jedna čiara: kým ju cena neprerazí alebo nevyprší, nový pivot ju
nenahradí. Dotyk je samostatná epizóda barov, ktoré sa k čiare priblížili — tretí dotyk môže
prísť aj po vzniku čiary a čiara sa stane obchodovateľnou až vtedy (`minTouches`).

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
    #: časy pivotov, ktoré už boli kotvou nejakej čiary — z jedného bodu vedie najviac jedna
    used_anchors: set = field(default_factory=set)
    #: čiary a pivoty, ktoré vznikli pri poslednom `on_htf_bar` (na kreslenie)
    new_lines: list = field(default_factory=list)
    new_pivots: list = field(default_factory=list)
    #: čiary, ktoré pri poslednom `on_htf_bar` skončili (prerazené, nahradené, vypršané): (čiara, koniec v ms)
    ended: list = field(default_factory=list)

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
        self.ended = []
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
                self.ended.append((ln, b.time + self.tf_ms))
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
        if len(self.used_anchors) > 4 * int(self.cfg.maxPivots) + 50:   # staré pivoty už v okne nie sú
            oldest = min(x.t for x in (self.highs + self.lows)) if (self.highs or self.lows) else 0
            self.used_anchors = {u for u in self.used_anchors if u[1] >= oldest}
        store.append(p)
        if len(store) > int(self.cfg.maxPivots):
            del store[0]
        self.new_pivots.append((kind, p))
        # Jedna čiara na stranu: kým žije, nový pivot ju nenahradí (ak je pri nej, je to dotyk,
        # ktorý už započítal `on_htf_bar`). Nová čiara vzniká až po prerazení alebo vypršaní.
        if getattr(self, kind) is not None:
            return
        line = self._best_line(store, kind)
        if line is not None:
            setattr(self, kind, line)
            self.new_lines.append(line)

    def _best_line(self, store: list, kind: str) -> Line | None:
        """Čiara ako by ju nakreslil človek: od začiatku trendu po najnovší pivot.

        Druhá kotva je najnovší pivot. Prvá je najvyšší vrchol (odpor), resp. najnižšie dno
        (podpora) spomedzi starších pivotov — začiatok trendu —, ak je čiara z neho platná;
        inak ďalší v poradí. Platná znamená, že medzi kotvami ani za druhou kotvou ju
        nepreráža žiadna sviečka (knôt alebo telo podľa `anchorMode`, s toleranciou dotyku).
        """
        cfg = self.cfg
        b = store[-1]
        tol = self._tol()
        i_now = self.count - 1
        res = kind == "res"
        # kandidáti na prvú kotvu: od najvýraznejšieho (najvyšší vrchol / najnižšie dno)
        cands = sorted(store[:-1], key=lambda x: -x.price if res else x.price)
        for a in cands:
            if (kind, a.t) in self.used_anchors:
                continue            # z tohto bodu už čiara viedla — žiadne vejáre z jedného bodu
            gap = b.i - a.i
            if gap < cfg.minAnchorGap:
                continue
            if cfg.lineSlope is LineSlope.CLASSIC:
                if res and not b.price < a.price:
                    continue
                if not res and not b.price > a.price:
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
            ok, touches, last = True, 2, -10
            for i in range(a.i + 1, i_now + 1):
                if i == b.i:
                    continue
                x = self._bar(i)
                if x is None:
                    ok = False
                    break
                v = ln.value(x.time)
                val = self._hi(x) if res else self._lo(x)
                if (res and val > v + tol) or (not res and val < v - tol):
                    ok = False          # sviečka prechádza čiarou — to nie je trendovka
                    break
                near = val >= v - tol if res else val <= v + tol
                if near and abs(i - a.i) > 1 and abs(i - b.i) > 1:
                    if i - last > 1:
                        touches += 1
                    last = i
            if not ok:
                continue
            ln.touches, ln.last_touch_i = touches, last
            self._uid += 1
            ln.uid = self._uid
            self.used_anchors.add((kind, a.t))
            self.used_anchors.add((kind, b.t))
            return ln
        return None
