"""Support / Resistance — zhluky opakovaných dotykov tej istej ceny.

Replika Pine riadkov 822–1132.

Každý potvrdený swing (vlastný lookback `srSwingLen`) sa skúsi „prilepiť" k už
existujúcej úrovni, ak je od nej vzdialený menej ako `srClusterPoints` — tým sa
počítajú opakované dotyky. Pivot sa počíta z **close**, nie z knôtu: úroveň má
vzniknúť tam, kde sa cena naozaj zavrela na lokálnom extréme a otočila, nie
kdekoľvek ju len na chvíľu prepichla.

Úroveň nie je čiara, ale **oblasť** — drží si skutočný rozsah (min/max) dotykov.

Kreslenie beží v Pine len na `barstate.islast`, lebo zloženie zhlukov sa mení
s cenou (triedi sa podľa vzdialenosti od `close`). Tu to zodpovedá `render()`,
ktoré zavolá nástroj/adaptér po dobehnutí, nie `on_bar` na každom bare.

Typ úrovne je **dynamický**: support/resistance nie je vlastnosť úrovne, ale jej
vzťahu k aktuálnej cene — prerazená resistance sa často stane novým supportom.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..drawing import (
    PAL,
    DrawBox,
    DrawCommand,
    DrawKind,
    DrawLabel,
    LabelStyle,
    with_alpha,
)
from ..history import BarHistory
from ..types import Bar, InstrumentSpec
from .structure import pivot

__all__ = ["SrLevel", "SupportResistance"]

#: Pine `srZoneHalfWidth` — zóna má fixnú výšku 3 cenové body.
_HALF_WIDTH = 1.5
#: Pine `srLevelMax`.
_MAX_LEVELS = 150


@dataclass(slots=True)
class SrLevel:
    """Jedna úroveň — priemer dotykov + ich skutočný rozsah."""

    price: float
    touches: int
    #: +1 vznikla z pivot-highov, -1 z pivot-lowov. Na kreslenie sa NEPOUŽÍVA,
    #: typ sa prepočítava dynamicky podľa polohy ceny (viď docstring modulu).
    typ: int
    first_ms: int
    low: float
    high: float
    zone_spawned: bool = False


class SupportResistance:
    """Eviduje úrovne a na požiadanie ich vykreslí."""

    __slots__ = ("cfg", "inst", "levels")

    def __init__(self, cfg, inst: InstrumentSpec) -> None:
        self.cfg = cfg
        self.inst = inst
        self.levels: list[SrLevel] = []

    # -- zbieranie dotykov ------------------------------------------------ #

    def on_bar(self, bar: Bar, history: BarHistory) -> list[int]:
        """Zaznamená dotyky z tohto baru. Vráti indexy dotknutých úrovní.

        Indexy potrebuje `enableSrTrading` — z úrovne, ktorá prvýkrát dosiahla
        `srMinTouches`, sa spawne obchodovateľná zóna (Pine `f_maybeSpawnSrZone`).
        """
        length = self.cfg.srSwingLen
        touched: list[int] = []

        piv_hi = pivot(history, length, source="close", high=True)
        if piv_hi is not None:
            touched.append(self._add_touch(piv_hi, 1, history[length].time))
        piv_lo = pivot(history, length, source="close", high=False)
        if piv_lo is not None:
            touched.append(self._add_touch(piv_lo, -1, history[length].time))

        self._forget_old(bar)
        return touched

    def _add_touch(self, price: float, typ: int, ts_ms: int) -> int:
        """Pine `addSrTouch` — prilepí k existujúcej úrovni alebo založí novú."""
        tol = self.cfg.srClusterPoints.resolve(self.inst, price=price)
        for i, lvl in enumerate(self.levels):
            if lvl.typ == typ and abs(lvl.price - price) <= tol:
                lvl.touches += 1
                lvl.price = (lvl.price + price) / 2
                lvl.low = min(lvl.low, price)
                lvl.high = max(lvl.high, price)
                return i

        self.levels.append(
            SrLevel(price=price, touches=1, typ=typ, first_ms=ts_ms, low=price, high=price)
        )
        if len(self.levels) > _MAX_LEVELS:
            self.levels.pop(0)
        return len(self.levels) - 1

    def _forget_old(self, bar: Bar) -> None:
        """Pine riadky 955–963 — úroveň staršia než `srLookbackDays` vypadne."""
        cutoff = self.cfg.srLookbackDays * 86_400_000
        if cutoff <= 0:
            return
        self.levels = [lvl for lvl in self.levels if bar.time - lvl.first_ms <= cutoff]

    # -- kreslenie -------------------------------------------------------- #

    def render(self, bar: Bar) -> list[DrawCommand]:
        """Pine riadky 1073–1131 — vykreslí sa až na poslednom bare."""
        if not self.cfg.showSR or not self.levels:
            return []

        # Triedime podľa VZDIALENOSTI od aktuálnej ceny — zobrazí sa `srMaxLevels`
        # najbližších úrovní, nie tie najsilnejšie kdekoľvek na grafe.
        order = sorted(self.levels, key=lambda l: abs(l.price - bar.close))
        shown = [l for l in order if l.touches >= self.cfg.srMinTouches][
            : self.cfg.srMaxLevels
        ]
        if not shown:
            return []

        out: list[DrawCommand] = []
        for n, group in enumerate(self._cluster(shown, bar)):
            out += self._draw_group(group, bar, n)
        return out

    def _cluster(self, shown: list[SrLevel], bar: Bar) -> list[list[SrLevel]]:
        """Zhluky blízkych úrovní — reťazovo a bez ohľadu na support/resistance.

        Bez toho by blízka S a R dali dve prekrývajúce sa čiary tesne vedľa seba.
        """
        tol = self.cfg.srClusterPoints.resolve(self.inst, price=bar.close)
        used = [False] * len(shown)
        groups: list[list[SrLevel]] = []

        for a, lvl in enumerate(shown):
            if used[a]:
                continue
            used[a] = True
            group = [lvl]
            grew = True
            while grew:
                grew = False
                for b, other in enumerate(shown):
                    if used[b]:
                        continue
                    if any(abs(g.price - other.price) <= tol for g in group):
                        used[b] = True
                        group.append(other)
                        grew = True
            groups.append(group)
        return groups

    def _draw_group(self, group: list[SrLevel], bar: Bar, n: int) -> list[DrawCommand]:
        lo = min(l.low for l in group)
        hi = max(l.high for l in group)
        if lo == hi:  # všetky dotyky presne na tej istej cene
            lo -= self.inst.tick_size * 2
            hi += self.inst.tick_size * 2
        mid = (lo + hi) / 2
        earliest = min(l.first_ms for l in group)
        touches = sum(l.touches for l in group)

        if len(group) >= 2:
            kind, color, text_color = DrawKind.SR_GOLDEN, PAL.AMBER.value, "#000000"
        else:
            # Cena NAD úrovňou = support, POD ňou = resistance.
            kind = DrawKind.SR_LEVEL
            color = PAL.LONG.value if bar.close > mid else PAL.SHORT.value
            text_color = "#ffffff"

        fill = with_alpha(color, 100 - self.cfg.srZoneSaturationPct)
        return [
            DrawBox(
                kind=kind,
                x1_ms=earliest,
                y1=mid + _HALF_WIDTH,
                x2_ms=bar.time,
                y2=mid - _HALF_WIDTH,
                border_color=fill,
                fill_color=fill,
                border_width=0,
                extend_right=True,
                obj_id=f"sr.{n}.box",
            ),
            DrawLabel(
                kind=kind,
                x_ms=bar.time,
                y=mid,
                text=f"{touches}x",
                color=text_color,
                style=LabelStyle.LEFT,
                bg_color=color,
                obj_id=f"sr.{n}.label",
            ),
        ]
