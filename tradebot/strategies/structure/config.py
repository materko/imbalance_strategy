"""Config stratégie tržnej štruktúry — 18 vstupov z `docs/sources/structure.pine`.

Názvy polí sú zhodné s Pine identifikátormi (rovnako ako pri IBS a demo). `leverage`
je rozšírenie portu (Freqtrade futures), Pine ho nemá.

Prahy sú zámerne **len v `atr`** — prah v absolútnych cenových bodoch platí presne na
jednom trhu a matica trhov (`cli matrix`) by ho aj tak musela prepočítať.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit, TradeDirection

__all__ = ["StructureConfig", "EntryMode", "ExitMode", "SlMode", "SessionTZ", "CONFIG_DIR"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryMode(str, Enum):
    """Pine `entryMode` — tri varianty toho istého enginu, nie tri stratégie."""

    #: vstup v smere NOVEJ štruktúry na zatvorení baru, ktorý CHoCH spôsobil
    CHOCH = "choch"
    #: vstup v smere pokračovania po BOS
    BOS = "bos"
    #: vstup PROTI CHoCH — CHoCH nadol znamená long (falošné prerazenie / odber likvidity)
    SWEEP = "sweep"


class ExitMode(str, Enum):
    """Pine `exitMode`."""

    #: take profit je násobok rizika (`rrRatio`)
    RR = "rr"
    #: obchod končí na ďalšej štruktúrnej udalosti v smere obchodu
    STRUCTURE = "structure"


class SlMode(str, Enum):
    """Pine `slMode`."""

    #: za posledným potvrdeným swingom v protismere, plus `slBuffer`
    SWING = "swing"
    #: pevný násobok ATR od vstupu (`slAtrMult`)
    ATR = "atr"


class SessionTZ(str, Enum):
    """Pine `sessionTZ` — v ktorom pásme sa čítajú hodiny obchodného okna."""

    UTC = "UTC"
    NEW_YORK = "America/New_York"
    LONDON = "Europe/London"
    TOKYO = "Asia/Tokyo"


SIZE_FIELDS: dict[str, SizeUnit] = {"minSwingSize": "atr", "slBuffer": "atr"}

ENUM_FIELDS: dict[str, type] = {
    "entryMode": EntryMode,
    "exitMode": ExitMode,
    "slMode": SlMode,
    "tradeDirection": TradeDirection,
    "sessionTZ": SessionTZ,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "swingLeft": (2, 20),
    "swingRight": (2, 20),
    "minSwingSize": (0, 3),
    "atrLen": (2, 100),
    "rrRatio": (1, 8),
    "slBuffer": (0, 1),
    "slAtrMult": (0.5, 5),
    "maxBars": (0, 500),
    "riskDollar": (0, 100000),
    "sessionStartH": (0, 23),
    "sessionEndH": (0, 23),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class StructureConfig(StrategyConfig):
    """Defaulty = Pine defaulty."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🎯 Štruktúra ----------------------------------------------------- #
    swingLeft: int = 5
    swingRight: int = 5
    minSwingSize: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    atrLen: int = 14
    # ---- 🚪 Vstup --------------------------------------------------------- #
    entryMode: EntryMode = EntryMode.CHOCH
    tradeDirection: TradeDirection = TradeDirection.BOTH
    # ---- 🛑 Výstup -------------------------------------------------------- #
    exitMode: ExitMode = ExitMode.RR
    rrRatio: float = 2.0
    slMode: SlMode = SlMode.SWING
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    slAtrMult: float = 1.5
    maxBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🕒 Seansa -------------------------------------------------------- #
    useSession: bool = False
    sessionTZ: SessionTZ = SessionTZ.UTC
    sessionStartH: int = 8
    sessionEndH: int = 16
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showStructure: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Páka vo Freqtrade futures — Pine ju nemá.
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.useSession and self.sessionStartH == self.sessionEndH:
            yield (f"sessionStartH == sessionEndH == {self.sessionStartH}: okno má nulovú dĺžku, "
                   "stratégia by neotvorila ani jeden obchod")
