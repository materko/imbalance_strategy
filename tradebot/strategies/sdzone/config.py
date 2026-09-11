"""Config stratégie SD Zones — supply/demand zóny v štýle „báza + impulz".

Metodika je zápis verejne popísaného postupu (Bernd Skorupinski, Online Trading Campus):
zóna vzniká tam, odkiaľ cena **impulzívne odišla** z krátkej konsolidácie, a obchoduje sa
**prvý návrat** do nej. Štyri formácie sú Rally-Base-Rally, Drop-Base-Drop (pokračovacie)
a Rally-Base-Drop, Drop-Base-Rally (obratové).

Čo z metodiky **nie je** v porte: COT dáta a sezónnosť. Sú to externé zdroje, ktoré tento
rámec nemá — bez nich je to cenová časť metodiky, nie celá metodika. Je to napísané aj
v `docs/ANALYTIKA.md`, aby sa na to pri čítaní výsledkov nezabudlo.

Rozdiel oproti stratégii `ibs`: tá v zóne hľadá imbalance cez päťstavový automat, tu sa
obchoduje samotný návrat do čerstvej zóny limitkou.

Prahy sú v ATR alebo v percentách, nie v cenových bodoch — inak by sa zóna na NAS100
a na XAU merala úplne inak.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["SDZoneConfig", "EntryMode", "PatternSet", "SlMode", "TpMode", "TradeDirection",
           "ZoneMode", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class ZoneMode(str, Enum):
    """Ako široko sa zóna kreslí."""

    PFZ = "pfz"   # úzka: telo bázy po extrém knôtu — presnejší vstup, častejšie ho cena minie
    WFZ = "wfz"   # široká: celý rozsah bázy od knôtu po knôt — istejšie vyplnenie, horšia cena


class PatternSet(str, Enum):
    """Ktoré formácie obchodovať."""

    ALL = "all"                    # všetky štyri
    CONTINUATION = "continuation"  # Rally-Base-Rally a Drop-Base-Drop
    REVERSAL = "reversal"          # Drop-Base-Rally a Rally-Base-Drop


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class EntryMode(str, Enum):
    """Ako sa vstupuje pri návrate do zóny."""

    LIMIT = "limit"    # limitka na okraji zóny — najlepšia cena, nemusí sa vyplniť
    CLOSE = "close"    # trhový vstup, keď sviečka zavrie vnútri zóny — istejšie, horšia cena
    REJECT = "reject"  # čaká sa na sviečku, ktorá zónu odmietne (zavrie mimo nej späť v smere)


class SlMode(str, Enum):
    ZONE = "zone"  # za vzdialenejšiu hranu zóny + buffer
    ATR = "atr"    # násobok ATR od vstupu


class TpMode(str, Enum):
    RR = "rr"              # násobok vzdialenosti SL
    OPPOSITE = "opposite"  # najbližšia opačná zóna, inak spadne na RR
    ATR = "atr"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "minSlDistance": "pct",
    "baseMaxWidthAtr": "atr",
    "impulseMinBodyAtr": "atr",
    "impulseMinMoveAtr": "atr",
    "slBufferAtr": "atr",
    "slAtrMult": "atr",
    "tpAtrMult": "atr",
}

ENUM_FIELDS: dict[str, type] = {
    "zoneMode": ZoneMode,
    "patterns": PatternSet,
    "tradeDirection": TradeDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
    "tpMode": TpMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "baseMaxBars": (1, 6),
    "baseMaxBodyPct": (5, 80),
    "baseMaxWidthAtr": (0.1, 5.0),
    "impulseMinBodyAtr": (0.1, 5.0),
    "impulseMinBodyPct": (10, 100),
    "impulseMinMoveAtr": (0.2, 10.0),
    "impulseMaxBars": (1, 10),
    "entryDepthPct": (0, 100),
    "maxZoneAgeBars": (5, 2000),
    "maxZones": (1, 200),
    "maxTradesPerDay": (1, 20),
    "atrLen": (2, 100),
    "slBufferAtr": (0.0, 2.0),
    "slAtrMult": (0.1, 10.0),
    "rrRatio": (0.5, 10.0),
    "tpAtrMult": (0.1, 20.0),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.1, 10.0),
    "maxHoldBars": (0, 2000),
    "trendMaLen": (5, 500),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class SDZoneConfig(StrategyConfig):
    """Supply/demand zóny: báza + impulz, obchoduje sa prvý návrat do čerstvej zóny."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🔍 Detekcia zóny ------------------------------------------------- #
    baseMaxBars: int = 3
    baseMaxBodyPct: int = 40
    baseMaxWidthAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.2, "atr"))
    impulseMinBodyAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.8, "atr"))
    impulseMinBodyPct: int = 55
    impulseMinMoveAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    impulseMaxBars: int = 3
    # ---- 📐 Zóna ---------------------------------------------------------- #
    zoneMode: ZoneMode = ZoneMode.WFZ
    patterns: PatternSet = PatternSet.ALL
    maxZoneAgeBars: int = 300
    maxZones: int = 40
    requireFresh: bool = True
    # ---- 🚪 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.LIMIT
    entryDepthPct: int = 0
    maxTradesPerDay: int = 3
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTrendFilter: bool = False
    trendMaLen: int = 200
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    slMode: SlMode = SlMode.ZONE
    atrLen: int = 14
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.15, "atr"))
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 3.0
    tpAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(3.0, "atr"))
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5
    maxHoldBars: int = 0
    closeAtWindowEnd: bool = False
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showZones: bool = True
    showPatterns: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    legacyPineSizing: bool = False
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def window_start_minutes(self) -> int:
        return self.tradeStartH * 60 + self.tradeStartM

    @property
    def window_end_minutes(self) -> int:
        return self.tradeEndH * 60 + self.tradeEndM

    def trades_pattern(self, continuation: bool) -> bool:
        if self.patterns is PatternSet.ALL:
            return True
        if self.patterns is PatternSet.CONTINUATION:
            return continuation
        return not continuation

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue (Pine ho v tom vzorci používa)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield (f"obchodné okno: koniec ({self.tradeEndH}:{self.tradeEndM:02d}) musí byť "
                   f"za začiatkom ({self.tradeStartH}:{self.tradeStartM:02d})")
        if self.closeAtWindowEnd and not self.useTradeWindow:
            yield "closeAtWindowEnd nemá zmysel bez zapnutého obchodného okna (useTradeWindow)"
        if self.impulseMinBodyPct <= self.baseMaxBodyPct:
            yield (f"impulseMinBodyPct={self.impulseMinBodyPct} musí byť väčšie než "
                   f"baseMaxBodyPct={self.baseMaxBodyPct}, inak by tá istá sviečka bola "
                   "bázou aj impulzom")
