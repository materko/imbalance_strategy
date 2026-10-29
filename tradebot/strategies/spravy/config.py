"""Config stratégie SPRÁVY 3.0 — zlato po červených správach USA, pre každú správu vlastné pravidlo.

Výskum 29. 10. 2026 (MGC 2021–2026, 12 typov správ, iCloud SPRAVY/vyskum/VYSKUM_SPRAVANIE_MGC_2026-10-29.md) ukázal,
že každá správa sa správa inak — preto 2.0 namiesto spoločných skupín TREND / FADE nesie **8 pravidiel** (`r1…` až `r8…`):

  * `rNEvent` — typ správy (prázdne = pravidlo vypnuté); jedna správa môže mať viac pravidiel (FOMC: pred, tlačovka),
  * `rNMode` — ``trend`` = vstup v smere nohy, ``fade`` = proti nej,
  * `rNFrom` → `rNTo` — noha v minútach od správy; **záporné od** = pohyb pred správou (−60 → 0 = hodina pred FOMC),
  * `rNEnter` — vstup trhom v T + toľko minút (≥ koniec nohy; tlačovka FOMC: noha 0 → 25, vstup 30),
  * `rNHold` — výstup trhom po toľkých minútach od vstupu,
  * `rNStop` — stop ako násobok nohy od vstupu (0 = za extrémom nohy + `slBuffer`),
  * `rNRR` — cieľ v násobkoch rizika (RRR 1 : N; 0 = bez cieľa, predvolene len PPI 1 : 3) — kto ho nedosiahne, zavrie sa v čase `rNHold`.

Predvolené pravidlá z výskumu a overenia 29. 10.: (1) FOMC proti driftu hodinu pred správou, výstup 16:55 NY;
(3) CPI a (6) JOLTS proti prvej hodine; (4) PPI proti prvým 15 min, stop za extrémom, cieľ 1 : 3, držať 3 h;
(5) PCE v smere nohy 15 → 60. Cieľ RRR má predvolene len PPI (rozhodnutie používateľa 29. 10.), ostatné idú bez cieľa na čas.
(2) tlačovka FOMC (14:30 v smere 14:00 → 14:25) je pripravená, ale vypnutá (prázdna správa) — s ňou PF prvého okna 0,95.
Ostatné správy sú vypnuté.
Jeden obchod naraz; pravidlá tej istej správy idú za sebou (držanie predchádzajúceho musí skončiť pred vstupom ďalšieho).

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

__all__ = ["SpravyConfig", "CONFIG_DIR", "Rule", "RULES", "MODES"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {"slBuffer": "atr", "minLeg": "atr"}
ENUM_FIELDS: dict[str, type] = {}
RULES = 8
MODES = ("trend", "fade")
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "atrLen": (2, 200), "sizeMinRisk": (0.0, 100.0), "riskDollar": (0, 100000), "leverage": (1, 125),
}
for _n in range(1, RULES + 1):
    CONSTRAINTS.update({f"r{_n}From": (-600, 600), f"r{_n}To": (-600, 600), f"r{_n}Enter": (-600, 600),
                        f"r{_n}Hold": (1, 2880), f"r{_n}Stop": (0.0, 20.0), f"r{_n}RR": (0.0, 50.0)})
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})
#: SPRÁVY 1.0 (do 29. 10. 2026) — spoločné skupiny TREND / FADE nahradili pravidlá po správach.
RETIRED_FIELDS: dict[str, str] = {k: "SPRÁVY 3.0: nahradené pravidlami r1…r8 (29. 10. 2026; tpR → rNRR)" for k in (
    "trendEvents", "trendFrom", "trendTo", "trendHold", "fadeEvents", "fadeFrom", "fadeTo", "fadeHold",
    "trendStopLeg", "fadeStopLeg", "tpR")}


@dataclass(frozen=True)
class Rule:
    """Jedno pravidlo (z polí `rN…`)."""
    no: int
    event: str
    trend: bool
    frm: int
    to: int
    enter: int
    hold: int
    stop: float
    rr: float = 0.0

    @property
    def label(self) -> str:
        """PRED = noha celá pred správou, inak TREND / FADE."""
        if self.to <= 0:
            return "PRED"
        return "TREND" if self.trend else "FADE"


@dataclass
class SpravyConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Zlato po červených správach USA: pre každú správu vlastné pravidlo (8 pravidiel), výstup v čase."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    RETIRED_FIELDS: ClassVar[dict[str, str]] = RETIRED_FIELDS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- ✅ Obchodované správy (pravidlo platí len pre zapnutú správu) ------------- #
    useFOMC: bool = True
    useFOMC_MIN: bool = False
    useCPI: bool = True
    useNFP: bool = False
    usePPI: bool = True
    useJOLTS: bool = True
    useRETAIL: bool = False
    usePCE: bool = True
    useGDP: bool = False
    useISM_M: bool = False
    useISM_S: bool = False
    useCLAIMS: bool = False
    # ---- 📰 Pravidlo 1 ---------------------------------------------------------- #
    r1Event: str = "FOMC"
    r1Mode: str = "fade"
    r1From: int = -60
    r1To: int = 0
    r1Enter: int = 0
    r1Hold: int = 175
    r1Stop: float = 10.0
    r1RR: float = 0.0
    # ---- 📰 Pravidlo 2 ---------------------------------------------------------- #
    r2Event: str = ""
    r2Mode: str = "trend"
    r2From: int = 0
    r2To: int = 25
    r2Enter: int = 30
    r2Hold: int = 145
    r2Stop: float = 0.0
    r2RR: float = 0.0
    # ---- 📰 Pravidlo 3 ---------------------------------------------------------- #
    r3Event: str = "CPI"
    r3Mode: str = "fade"
    r3From: int = 0
    r3To: int = 60
    r3Enter: int = 60
    r3Hold: int = 60
    r3Stop: float = 10.0
    r3RR: float = 0.0
    # ---- 📰 Pravidlo 4 ---------------------------------------------------------- #
    r4Event: str = "PPI"
    r4Mode: str = "fade"
    r4From: int = 0
    r4To: int = 15
    r4Enter: int = 15
    r4Hold: int = 180
    r4Stop: float = 0.0
    r4RR: float = 3.0
    # ---- 📰 Pravidlo 5 ---------------------------------------------------------- #
    r5Event: str = "PCE"
    r5Mode: str = "trend"
    r5From: int = 15
    r5To: int = 60
    r5Enter: int = 60
    r5Hold: int = 240
    r5Stop: float = 0.0
    r5RR: float = 0.0
    # ---- 📰 Pravidlo 6 ---------------------------------------------------------- #
    r6Event: str = "JOLTS"
    r6Mode: str = "fade"
    r6From: int = 0
    r6To: int = 60
    r6Enter: int = 60
    r6Hold: int = 60
    r6Stop: float = 10.0
    r6RR: float = 0.0
    # ---- 📰 Pravidlo 7 ---------------------------------------------------------- #
    r7Event: str = ""
    r7Mode: str = "trend"
    r7From: int = 0
    r7To: int = 15
    r7Enter: int = 15
    r7Hold: int = 60
    r7Stop: float = 0.0
    r7RR: float = 0.0
    # ---- 📰 Pravidlo 8 ---------------------------------------------------------- #
    r8Event: str = ""
    r8Mode: str = "trend"
    r8From: int = 0
    r8To: int = 15
    r8Enter: int = 15
    r8Hold: int = 60
    r8Stop: float = 0.0
    r8RR: float = 0.0
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------------- #
    #: ATR grafu (Wilder) — jednotka rezervy stopu a minimálnej nohy.
    atrLen: int = 14
    #: Stop za extrémom nohy na strane proti pozícii + rezerva.
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    #: Noha musí mať aspoň toľko (0 = každá).
    minLeg: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
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

    def rules(self) -> list[Rule]:
        """Platné pravidlá (vyplnená a zapnutá správa `use<TYP>`) v poradí 1…8."""
        out = []
        for n in range(1, RULES + 1):
            ev = str(getattr(self, f"r{n}Event") or "").strip().upper()
            if not ev or not getattr(self, f"use{ev}", False):
                continue
            out.append(Rule(n, ev, str(getattr(self, f"r{n}Mode")).strip().lower() == "trend",
                            int(getattr(self, f"r{n}From")), int(getattr(self, f"r{n}To")), int(getattr(self, f"r{n}Enter")),
                            int(getattr(self, f"r{n}Hold")), float(getattr(self, f"r{n}Stop")), float(getattr(self, f"r{n}RR"))))
        return out

    def _problems(self) -> Iterable[str]:
        for n in range(1, RULES + 1):
            ev = str(getattr(self, f"r{n}Event") or "").strip().upper()
            if not ev:
                continue
            if ev not in TYPES:
                yield f"pravidlo {n}: neznámy typ správy {ev} (poznám {', '.join(TYPES)})"
            mode = str(getattr(self, f"r{n}Mode")).strip().lower()
            if mode not in MODES:
                yield f"pravidlo {n}: režim {mode!r} — len trend alebo fade"
            fr, to, en = (int(getattr(self, f"r{n}{k}")) for k in ("From", "To", "Enter"))
            if fr >= to:
                yield f"pravidlo {n}: noha musí mať od < do ({fr} → {to})"
            if en < to:
                yield f"pravidlo {n}: vstup ({en}) nesmie byť pred koncom nohy ({to})"
            rr = float(getattr(self, f"r{n}RR"))
            if 0 < rr < 0.5:
                yield f"pravidlo {n}: RRR {rr} — cieľ najmenej 0,5 R (alebo 0 = bez cieľa)"
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        try:
            parse_add(self.newsAdd)
            parse_skip(self.newsSkip)
        except ValueError as e:
            yield f"kalendár (newsAdd / newsSkip): {e}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
