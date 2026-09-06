"""Elliott Waves — replika Pine riadkov 1256–1474.

Automatické počítanie Elliottových vĺn je z princípu subjektívne (viacero
platných interpretácií môže existovať naraz). Modul preto vždy zobrazuje len
**jednu, najaktuálnejšiu** interpretáciu poslednej zigzag sekvencie a prekresľuje
sa zakaždým, keď sa zigzag zmení. Je to pomocná vizualizácia, nie predikcia.

Tri prísne Elliottove pravidlá sú tu **povinné** (na rozdiel od Fibonacci pomerov,
ktoré sú len odporúčania):

1. vlna 2 sa nesmie vrátiť za začiatok vlny 1
2. vlna 3 nesmie byť najkratšia z vĺn 1, 3, 5
3. vlna 4 sa nesmie prekrývať s cenovým územím vlny 1

Vzácne „diagonal" formácie, kde pravidlo 3 neplatí, sa vedome nerozlišujú — je to
známe zjednodušenie, nie chyba.

Kreslí sa vždy aspoň „kostra" posledných zigzag bodov, aby bolo vidieť, že modul
žije aj vtedy, keď práve neexistuje pravidlami potvrdený 5-vlnový počet.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..drawing import (
    DrawBox,
    DrawCommand,
    DrawKind,
    DrawLabel,
    DrawLine,
    LabelStyle,
    LineStyle,
    with_alpha,
)
from ..history import BarHistory
from ..types import Bar, InstrumentSpec
from .structure import pivot

__all__ = ["ElliottWaves", "ZigZagPoint"]

#: Pine `ewMaxZzPoints`.
_MAX_POINTS = 50


@dataclass(slots=True)
class ZigZagPoint:
    price: float
    ts_ms: int
    #: +1 pivot high, -1 pivot low
    typ: int


class ElliottWaves:
    """Zigzag + rozpoznanie impulzu. `on_bar` každý bar, `render()` na konci."""

    __slots__ = ("cfg", "inst", "step_ms", "points", "_changed")

    def __init__(self, cfg, inst: InstrumentSpec, step_ms: int) -> None:
        self.cfg = cfg
        self.inst = inst
        #: Pine `ewProjExtendBars` je v BAROCH, nie v minútach.
        self.step_ms = step_ms
        self.points: list[ZigZagPoint] = []
        self._changed = False

    # -- zigzag ----------------------------------------------------------- #

    def on_bar(self, bar: Bar, history: BarHistory) -> None:
        length = self.cfg.ewSwingLen
        piv_hi = pivot(history, length, high=True)
        if piv_hi is not None:
            self._changed |= self._add(piv_hi, history[length].time, 1, bar)
        piv_lo = pivot(history, length, high=False)
        if piv_lo is not None:
            self._changed |= self._add(piv_lo, history[length].time, -1, bar)

    def _add(self, price: float, ts_ms: int, typ: int, bar: Bar) -> bool:
        """Pine `ewAddPoint`. Vráti True, ak pribudol NOVÝ bod (nie len posun).

        Rovnaký typ pivota len posunie posledný bod, ak je extrémnejší. Opačný typ
        založí nový bod, ale len keď je vlna aspoň `ewMinWavePoints` veľká — inak
        by zigzag chytal každý šum.
        """
        if not self.points:
            self.points.append(ZigZagPoint(price, ts_ms, typ))
            return True

        last = self.points[-1]
        if typ == last.typ:
            more_extreme = price > last.price if typ == 1 else price < last.price
            if more_extreme:
                last.price = price
                last.ts_ms = ts_ms
            return False

        min_wave = self.cfg.ewMinWavePoints.resolve(self.inst, price=bar.close)
        if abs(price - last.price) < min_wave:
            return False

        self.points.append(ZigZagPoint(price, ts_ms, typ))
        if len(self.points) > _MAX_POINTS:
            self.points.pop(0)
        return True

    # -- kreslenie -------------------------------------------------------- #

    def render(self, bar: Bar, history: BarHistory) -> list[DrawCommand]:
        cfg = self.cfg
        if not cfg.showElliott or len(self.points) < 2:
            return []

        color = cfg.ewLineColor
        out: list[DrawCommand] = []

        # Kostra posledných bodov — tenká, priesvitná.
        tail = self.points[-7:]
        out += self._lines(tail, with_alpha(color, 60), 1, "tail")

        offset = self._label_offset(history)
        if len(self.points) >= 6 and self._valid_impulse(self.points[-6:]):
            pts = self.points[-6:]
            out += self._lines(pts, color, 2, "imp")
            if cfg.ewShowLabels:
                out += self._labels(pts, offset, color)
            if cfg.ewShowProjection:
                out += self._abc_target(pts, color)
        elif len(self.points) >= 5 and self._valid_partial(self.points[-5:]):
            pts = self.points[-5:]
            out += self._lines(pts, color, 2, "par")
            if cfg.ewShowLabels:
                out += self._labels(pts, offset, color)
            if cfg.ewShowProjection:
                out += self._wave5_target(pts, color)
        return out

    def _label_offset(self, history: BarHistory) -> float:
        """Pine ``(highest(high,50) - lowest(low,50)) * 0.02``."""
        n = min(50, len(history))
        if n == 0:
            return 0.0
        hi = max(history[i].high for i in range(n))
        lo = min(history[i].low for i in range(n))
        return (hi - lo) * 0.02

    @staticmethod
    def _direction(pts: list[ZigZagPoint]) -> int:
        """Impulz začínajúci v pivot-lowe ide hore."""
        return 1 if pts[0].typ == -1 else -1

    def _valid_impulse(self, pts: list[ZigZagPoint]) -> bool:
        """Pine `f_ewValidImpulse` — všetky tri prísne pravidlá."""
        d = self._direction(pts)
        p0, p1, p2, p3, p4, p5 = (p.price for p in pts)
        len1, len3, len5 = abs(p1 - p0), abs(p3 - p2), abs(p5 - p4)
        rule1 = p2 > p0 if d == 1 else p2 < p0
        rule2 = not (len3 < len1 and len3 < len5)
        rule3 = p4 > p1 if d == 1 else p4 < p1
        return rule1 and rule2 and rule3

    def _valid_partial(self, pts: list[ZigZagPoint]) -> bool:
        """Pine `f_ewValidPartial` — vlny 1–4, pravidlo 2 sa ešte nedá overiť."""
        d = self._direction(pts)
        p0, p1, p2, _p3, p4 = (p.price for p in pts)
        rule1 = p2 > p0 if d == 1 else p2 < p0
        rule3 = p4 > p1 if d == 1 else p4 < p1
        return rule1 and rule3

    def _lines(self, pts: list[ZigZagPoint], color: str, width: int, tag: str):
        return [
            DrawLine(
                kind=DrawKind.ELLIOTT_WAVE,
                x1_ms=a.ts_ms,
                y1=a.price,
                x2_ms=b.ts_ms,
                y2=b.price,
                color=color,
                width=width,
                obj_id=f"ew.{tag}.{i}",
            )
            for i, (a, b) in enumerate(zip(pts, pts[1:]))
        ]

    def _labels(self, pts: list[ZigZagPoint], offset: float, color: str):
        return [
            DrawLabel(
                kind=DrawKind.ELLIOTT_WAVE,
                x_ms=p.ts_ms,
                y=p.price + offset if p.typ == 1 else p.price - offset,
                text=str(i),
                color=color,
                style=LabelStyle.NONE,
                above=p.typ == 1,
                obj_id=f"ew.lbl.{i}",
            )
            for i, p in enumerate(pts)
        ]

    def _proj_span_ms(self) -> int:
        return self.cfg.ewProjExtendBars * self.step_ms

    def _abc_target(self, pts: list[ZigZagPoint], color: str) -> list[DrawCommand]:
        """Cieľ celej ABC korekcie — 38,2 % až 61,8 % retracement impulzu.

        Po dokončenom 5-vlnovom impulze ešte nevieme, kde skončí vlna A, takže sa
        používa bežne odporúčaná zóna pre celú korekciu naraz (guideline, nie pravidlo).
        """
        d = self._direction(pts)
        p0, p5 = pts[0].price, pts[-1].price
        total = abs(p5 - p0)
        a = p5 - 0.618 * total if d == 1 else p5 + 0.618 * total
        b = p5 - 0.382 * total if d == 1 else p5 + 0.382 * total
        return self._proj_box(pts[-1].ts_ms, max(a, b), min(a, b), color, "ABC ciel")

    def _wave5_target(self, pts: list[ZigZagPoint], color: str) -> list[DrawCommand]:
        """Cieľ vlny 5 — všetky tri štandardné odhady naraz ako jedna zóna.

        1. rovnosť s vlnou 1
        2. 61,8 % celkového pohybu vĺn 1–3
        3. 123,6 % až 161,8 % dĺžky vlny 4, meranej od jej konca
        """
        d = self._direction(pts)
        p0, p1, _p2, p3, p4 = (p.price for p in pts)
        wave1, move13, wave4 = abs(p1 - p0), abs(p3 - p0), abs(p4 - p3)
        s = 1 if d == 1 else -1
        levels = [
            p4 + s * wave1,
            p4 + s * 0.618 * move13,
            p4 + s * 1.236 * wave4,
            p4 + s * 1.618 * wave4,
        ]
        out = self._proj_box(pts[-1].ts_ms, max(levels), min(levels), color, "Vlna 5 ciel")
        eq = levels[0]
        out.append(
            DrawLine(
                kind=DrawKind.ELLIOTT_PROJ,
                x1_ms=pts[-1].ts_ms,
                y1=eq,
                x2_ms=pts[-1].ts_ms + self._proj_span_ms(),
                y2=eq,
                color=color,
                style=LineStyle.DASHED,
                obj_id="ew.proj.eq",
            )
        )
        return out

    def _proj_box(
        self, left_ms: int, top: float, bot: float, color: str, text: str
    ) -> list[DrawCommand]:
        right = left_ms + self._proj_span_ms()
        return [
            DrawBox(
                kind=DrawKind.ELLIOTT_PROJ,
                x1_ms=left_ms,
                y1=top,
                x2_ms=right,
                y2=bot,
                border_color=color,
                fill_color=with_alpha(color, 85),
                obj_id="ew.proj.box",
            ),
            DrawLabel(
                kind=DrawKind.ELLIOTT_PROJ,
                x_ms=right,
                y=(top + bot) / 2,
                text=text,
                color=color,
                style=LabelStyle.NONE,
                obj_id="ew.proj.label",
            ),
        ]
