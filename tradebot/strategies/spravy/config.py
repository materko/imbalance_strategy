"""Config stratégie SPRÁVY 1.0 — zlato po červených správach USA: trend po Fede, návrat po inflácii.

Prieskum 29. 10. 2026 (MGC 2021–2026, 12 typov červených správ, iCloud SPRAVY-FOREXFACTORY):

  * **TREND** (`trendEvents`, default FOMC a PCE): smer nohy T+`trendFrom` → T+`trendTo` minút po správe
    pokračuje; vstup trhom v jej smere, výstup po `trendHold` minútach (odložené 2025–26 PF 3,5),
  * **FADE** (`fadeEvents`, default CPI, PPI, JOLTS): prvý pohyb T+`fadeFrom` → T+`fadeTo` sa vracia;
    vstup trhom proti nemu, výstup po `fadeHold` minútach (PF 1,6, 6 / 6 rokov),
  * **stop** za extrémom nohy na strane proti pozícii + `slBuffer`, alebo `trendStopLeg` / `fadeStopLeg` × veľkosť nohy
    od vstupu (FADE default 10 × = len poistka, prieskum: tesný stop návrat vyberie); voliteľný cieľ `tpR` × riziko (0 = len čas),
  * veľkosť: profil berie **pevný počet kontraktov** (`fixedQty`) — veľkosť z rizika pri tesnom stope nafúkne pozíciu
    a obchody s malou nohou prevážia (PF spolu 1,11 vs 2,18 s 1 kontraktom),
  * noha musí byť aspoň `minLeg` (v ATR grafu); jeden obchod na správu, nový len bez otvorenej pozície.

Čas správ je New York (`calendar.json`, prevod na UTC pre každý deň zvlášť). Opravy kalendára bez zmeny kódu:
`newsAdd`, `newsSkip`. Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_confirm import (ENTRY_CONFIRM_CONSTRAINTS, ENTRY_CONFIRM_ENUMS, ENTRY_CONFIRM_FIELD_NAMES,
                                         EntryConfirmFields)
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

from .calendar import TYPES, parse_add, parse_skip

__all__ = ["SpravyConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {"slBuffer": "atr", "minLeg": "atr"}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "trendFrom": (0, 600), "trendTo": (1, 600), "trendHold": (1, 2880),
    "fadeFrom": (0, 600), "fadeTo": (1, 600), "fadeHold": (1, 2880),
    "atrLen": (2, 200), "sizeMinRisk": (0.0, 100.0), "trendStopLeg": (0.0, 10.0), "fadeStopLeg": (0.0, 10.0), "tpR": (0.0, 50.0), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


def _types(text: str) -> set[str]:
    return {t.strip().upper() for t in (text or "").split(",") if t.strip()}


@dataclass
class SpravyConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Zlato po červených správach USA: trend po FOMC / PCE, návrat po CPI / PPI / JOLTS, výstup v čase."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📈 TREND (pokračovanie po správe) ----------------------------------------- #
    #: Typy správ oddelené čiarkou (FOMC, FOMC_MIN, CPI, NFP, PPI, PCE, GDP, RETAIL, JOLTS, ISM_M, ISM_S, CLAIMS).
    trendEvents: str = "FOMC,PCE"
    #: Noha od / do (minúty po správe); vstup na jej konci v jej smere.
    trendFrom: int = 15
    trendTo: int = 60
    #: Držať najviac toľko minút od vstupu.
    trendHold: int = 240
    # ---- 🔁 FADE (návrat po správe) ------------------------------------------------- #
    fadeEvents: str = "CPI,PPI,JOLTS"
    fadeFrom: int = 0
    fadeTo: int = 60
    fadeHold: int = 60
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------------- #
    #: ATR grafu (Wilder) — jednotka rezervy stopu a minimálnej nohy.
    atrLen: int = 14
    #: Stop za extrémom nohy na strane proti pozícii + rezerva.
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    #: Stop ako násobok veľkosti nohy od vstupu (0 = za extrémom nohy + `slBuffer`) — TREND / FADE zvlášť.
    trendStopLeg: float = 0.0
    fadeStopLeg: float = 10.0
    #: Noha musí mať aspoň toľko (0 = každá).
    minLeg: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Cieľ v násobkoch rizika; 0 = bez cieľa, len výstup v čase.
    tpR: float = 0.0
    allowLong: bool = True
    allowShort: bool = True
    # ---- 📅 Kalendár (opravy bez zmeny kódu) ---------------------------------------- #
    #: Pridať správy: "YYYY-MM-DD HH:MM TYP; …" (čas New York).
    newsAdd: str = ""
    #: Vynechať správy: "YYYY-MM-DD TYP; …".
    newsSkip: str = ""
    # ---- 💰 Veľkosť ------------------------------------------------------------------ #
    #: Riziko na obchod v $ (pri vypnutom pevnom počte kontraktov): strata na stope ≤ toľko.
    riskDollar: float = 500.0
    #: Veľkosť z rizika ráta so vzdialenosťou stopu aspoň toľko ATR grafu — tesný stop pozíciu nenafúkne
    #: (strata na stope je potom menšia než riziko, nikdy väčšia); 0 = presne podľa stopu.
    sizeMinRisk: float = 0.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------------- #
    showLegs: bool = True
    # ---- rozšírenia portu ------------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def trend_types(self) -> set[str]:
        return _types(self.trendEvents)

    @property
    def fade_types(self) -> set[str]:
        return _types(self.fadeEvents)

    def _problems(self) -> Iterable[str]:
        unknown = (self.trend_types | self.fade_types) - set(TYPES)
        if unknown:
            yield f"neznáme typy správ: {', '.join(sorted(unknown))} (poznám {', '.join(TYPES)})"
        both = self.trend_types & self.fade_types
        if both:
            yield f"typ nemôže byť naraz TREND aj FADE: {', '.join(sorted(both))}"
        if self.trendFrom >= self.trendTo:
            yield "TREND: noha musí mať trendFrom < trendTo"
        if self.fadeFrom >= self.fadeTo:
            yield "FADE: noha musí mať fadeFrom < fadeTo"
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        try:
            parse_add(self.newsAdd)
            parse_skip(self.newsSkip)
        except ValueError as e:
            yield f"kalendár (newsAdd / newsSkip): {e}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
