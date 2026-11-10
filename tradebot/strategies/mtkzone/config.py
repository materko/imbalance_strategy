"""Config stratégie MTK ZONE — SD zóny z vyšších TF (klasické, vrchol volume profilu, nárast klasického objemu)
a vstupy limit na zónu / IBS / pin bar na grafe. Predloha: Pine „VP SD ZÓNY 50 — stratégia“ (10. 11. 2026,
iCloud VOLUME-PROFILE, nie v repozitári), postup `docs/VYSVETLIVKA.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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

__all__ = ["MtkZoneConfig", "TradeDirection", "VwapMode", "VwapAnchor", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class VwapMode(str, Enum):
    OFF = "off"
    WITH = "with"          # long nad VWAP, short pod
    AGAINST = "against"    # long pod VWAP, short nad (návrat k VWAP)


class VwapAnchor(str, Enum):
    DAY = "day"            # obchodný deň CME (od 18:00 New York)
    NY = "ny"              # otvorenie New Yorku 9:30 (pred 9:30 pokračuje od predošlého otvorenia)
    WEEK = "week"
    MONTH = "month"


SIZE_FIELDS: dict[str, SizeUnit] = {"minImbSize": "abs", "pbMinRange": "abs"}
ENUM_FIELDS: dict[str, type] = {"tradeDirection": TradeDirection, "vwapMode": VwapMode, "vwapAnchor": VwapAnchor}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "zoneTf1": (1, 240), "zoneTf2": (1, 240), "pocEvery": (1, 200), "minConf": (1, 3),
    "impMult": (0.3, 10.0), "volSpike": (1.0, 20.0), "impMultVol": (0.3, 10.0), "baseMax": (1, 6),
    "baseBodyMax": (0.1, 5.0), "minScore": (0, 100), "maxZones": (1, 50), "atrLen": (2, 200), "volLen": (2, 500),
    "lookback": (10, 500), "rows": (10, 100), "peakMin": (0.5, 50.0),
    "modelBars": (1, 300), "imbLookback": (1, 50), "imbMaxDistTicks": (0, 2000), "st1Max": (1, 50),
    "st2Max": (1, 50), "st2ConfTicks": (0, 200), "st3Max": (1, 50), "st5Max": (1, 50), "ibsSlLookback": (1, 100),
    "pbRatio": (1.0, 20.0), "pbBodyPos": (5, 50),
    "rrRatio": (0.5, 20.0), "slBufTicks": (0, 200), "riskDollar": (0, 100000), "qty": (0.001, 1000),
    "maxRiskTicks": (0, 100000), "minGap": (0, 1000), "maxDist": (0, 100000),
    "sessStart": (0, 2359), "sessEnd": (0, 2359), "maxZoneAge": (0, 100000), "minEntryScore": (0, 100),
    "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class MtkZoneConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """SD zóny z 5m / 15m (tri zdroje, min. počet potvrdení) a vstupy limit / IBS / pin bar na grafe."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 1 · Zóny — odkiaľ sa berú --------------------------------------------- #
    useZ1: bool = True
    zoneTf1: int = 5
    useZ2: bool = False
    zoneTf2: int = 15
    useClassic: bool = True
    usePeak: bool = True
    useVolSurge: bool = True
    usePocZone: bool = False
    pocEvery: int = 10
    # ---- 2 · Zóny — pravidlá ------------------------------------------------------ #
    minConf: int = 2
    impMult: float = 1.5
    volSpike: float = 2.0
    impMultVol: float = 0.5
    baseMax: int = 3
    baseBodyMax: float = 0.6
    minScore: float = 40.0
    maxZones: int = 3
    atrLen: int = 14
    volLen: int = 20
    # ---- 3 · Volume profil ---------------------------------------------------------- #
    lookback: int = 50
    rows: int = 40
    peakMin: float = 3.0
    # ---- 4 · Vstupné modely ------------------------------------------------------------ #
    useLimit: bool = True
    useIBS: bool = False
    usePin: bool = False
    modelBars: int = 30
    imbLookback: int = 20
    minImbSize: SizeSpec = field(default_factory=lambda: SizeSpec(8.0, "abs"))
    imbMaxDistTicks: int = 40
    st1Max: int = 1
    st2Max: int = 10
    st2ConfTicks: int = 6
    st3Max: int = 4
    st5Max: int = 4
    ibsSlLookback: int = 10
    pbRatio: float = 4.0
    pbBodyPos: float = 20.0
    pbMinRange: SizeSpec = field(default_factory=lambda: SizeSpec(4.0, "abs"))
    # ---- 5 · Obchod ------------------------------------------------------------------------ #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    rrRatio: float = 1.0
    slBufTicks: int = 0
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 400.0
    maxRiskTicks: int = 0
    minGap: int = 0
    maxDist: float = 0.0
    # ---- 6 · Filtre ------------------------------------------------------------------------- #
    vwapMode: VwapMode = VwapMode.OFF
    vwapAnchor: VwapAnchor = VwapAnchor.DAY
    useSess: bool = False
    sessStart: int = 930
    sessEnd: int = 1600
    maxZoneAge: int = 0
    minEntryScore: float = 0.0
    # ---- 7 · Zobrazenie ---------------------------------------------------------------------- #
    showZones: bool = True
    showIbsDraw: bool = True
    # ---- rozšírenia portu ---------------------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        if not (self.useZ1 or self.useZ2):
            yield "zapni aspoň jeden TF zón (useZ1 / useZ2)"
        if not (self.useClassic or self.usePeak or self.useVolSurge or self.usePocZone):
            yield "zapni aspoň jeden zdroj zón"
        if not (self.useLimit or self.useIBS or self.usePin):
            yield "zapni aspoň jeden vstupný model (useLimit / useIBS / usePin)"
        if self.sessStart % 100 >= 60 or self.sessEnd % 100 >= 60:
            yield "sessStart / sessEnd sú v tvare HHMM (minúty < 60)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
