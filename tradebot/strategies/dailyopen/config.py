"""Config stratégie DAILY OPEN 1.0 — prieraz nad zavretím polnoci NY.

Podľa videa Ali Caseyho (StatOasis) „Easy Nasdaq Scalping Strategy Anyone Can Try" (6. 10. 2026):

  * NQ futures, 60m graf, len long,
  * o polnoci NY sa zapamätá zavretie sviečky, ktorá končí o 0:00 („close of midnight"),
  * od 8:00 NY: keď je cena nad týmto zavretím + 30 bodov → long (prieraz),
  * stop 1 000 $ na NQ (= 50 bodov), výstup na konci dennej seansy 16:00 NY, jeden obchod za deň,
  * varianty z videa: výstup 14:00, prah 40 bodov a stop 800 $ (40 bodov).

Video hovorí v bodoch NQ; prah a stop sú preto v bodoch ceny (`abs`) — na MNQ / NAS100 sedia 1 : 1.
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

__all__ = ["DailyOpenConfig", "BreakMode", "EntryMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryMode(str, Enum):
    STOP = "stop"    # stop order na úrovni (zavretie polnoci + prah) — prieraz kedykoľvek vnútri sviečky
    CLOSE = "close"  # market na zavretí sviečky, ktorá zavrie nad úrovňou


class BreakMode(str, Enum):
    ANY = "any"        # stačí prieraz zavretie + prah v okne vstupu (podmienka „po polnoci nad zavretím" je v ňom)
    BEFORE = "before"  # cena musí byť nad zavretím polnoci už pred začiatkom okna vstupu (v noci)


class TradeDirection(str, Enum):
    LONG_ONLY = "Long only"   # video
    BOTH = "Both"             # aj short zrkadlovo: pod zavretím − prah
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "breakPts": "abs",
    "slPts": "abs",
    "tpPts": "abs",
}

ENUM_FIELDS: dict[str, type] = {
    "entryMode": EntryMode,
    "breakMode": BreakMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "refH": (0, 23),
    "refM": (0, 59),
    "entryStartH": (0, 23),
    "entryStartM": (0, 59),
    "entryEndH": (0, 23),
    "entryEndM": (0, 59),
    "exitH": (0, 23),
    "exitM": (0, 59),
    "maxTradesPerDay": (1, 10),
    "qty": (0.001, 1000),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class DailyOpenConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Long, keď cena od rána prerazí zavretie polnoci NY o prah; stop v bodoch, výstup v čase."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 🕛 Úroveň (zavretie polnoci, čas New York) ------------------------- #
    #: Čas zavretia sviečky, ktorej close je úroveň (video: polnoc).
    refH: int = 0
    refM: int = 0
    # ---- 🚀 Vstup ---------------------------------------------------------- #
    breakPts: SizeSpec = field(default_factory=lambda: SizeSpec(30.0, "abs"))
    entryMode: EntryMode = EntryMode.STOP
    breakMode: BreakMode = BreakMode.ANY
    entryStartH: int = 8
    entryStartM: int = 0
    entryEndH: int = 16
    entryEndM: int = 0
    tradeDirection: TradeDirection = TradeDirection.LONG_ONLY
    maxTradesPerDay: int = 1
    weekdaysOnly: bool = True
    # ---- 🚪 Výstup --------------------------------------------------------- #
    slPts: SizeSpec = field(default_factory=lambda: SizeSpec(50.0, "abs"))
    #: Cieľ v bodoch; 0 = bez cieľa (video: drží do konca dňa).
    tpPts: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    #: Zatvoriť v čase `exitH:exitM` (a pri zmene dňa). Vypnuté = obchod drží do stopu / cieľa (treba `tpPts`).
    useExit: bool = True
    exitH: int = 16
    exitM: int = 0
    # ---- 💰 Veľkosť -------------------------------------------------------- #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showLevels: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def ref_minutes(self) -> int:
        return self.refH * 60 + self.refM

    @property
    def entry_start_minutes(self) -> int:
        return self.entryStartH * 60 + self.entryStartM

    @property
    def entry_end_minutes(self) -> int:
        return self.entryEndH * 60 + self.entryEndM

    @property
    def exit_minutes(self) -> int:
        return self.exitH * 60 + self.exitM

    def _problems(self) -> Iterable[str]:
        if not self.useExit and self.tpPts.value <= 0:
            yield "bez výstupu v čase (useExit vypnuté) treba cieľ tpPts > 0 — inak obchod nemá ako skončiť ziskom"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.slPts.value <= 0:
            yield "slPts musí byť > 0"
        if self.entry_end_minutes <= self.entry_start_minutes:
            yield "okno vstupu: koniec musí byť za začiatkom"
        if not (self.ref_minutes < self.entry_start_minutes or self.refH == 0 and self.refM == 0):
            yield "čas úrovne musí byť pred začiatkom okna vstupu"
        if self.exit_minutes < self.entry_start_minutes:
            yield "výstup musí byť po začiatku okna vstupu"
