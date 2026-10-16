"""Config stratégie NOA 1.0 — Noise Area (Concretum).

Podľa práce Zarattini, Aziz, Barbon (2024) „Beat the Market: An Effective Intraday Momentum Strategy
for S&P500 ETF (SPY)" (Concretum Research), seansa New York 9:30–16:00:

  * pásmo šumu pre každú minútu seansy: priemer |close / open dňa − 1| v tej istej minúte za `lookbackDays` dní,
  * horná hranica = max(open, včerajšie zavretie) × (1 + σ), dolná = min(open, včerajšie zavretie) × (1 − σ),
  * rozhoduje sa len na kontrolách každých `checkEvery` minút (od 10:00): zavretie nad hornou hranicou = long,
    pod dolnou = short,
  * výstup tiež len na kontrole: long, keď zavretie klesne pod max(hornú hranicu, VWAP), short zrkadlovo;
    o 16:00 sa zatvára všetko.

Pevný stop u brokera (`hardStopPct`) je len poistka proti prudkému pohybu medzi kontrolami — zdroj ho nemá.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from tradebot.core.types import SizeUnit

__all__ = ["NoaConfig", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "lookbackDays": (3, 60), "volMult": (0.2, 5.0), "checkEvery": (5, 120), "lastEntryMin": (30, 390),
    "hardStopPct": (0.0, 10.0), "maxTradesPerDay": (1, 50), "qty": (0.001, 1000), "riskDollar": (0, 100000),
    "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class NoaConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Intraday momentum: vstup, keď cena opustí pásmo šumu, výstup cez VWAP / hranicu pásma alebo o 16:00."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- ⚙️ Pásmo šumu ----------------------------------------------------- #
    #: Priemer pohybu od otvorenia za toľko predošlých dní. Zdroj: 14.
    lookbackDays: int = 14
    #: Násobok pásma. 1 = zdroj; vyššie = širšie pásmo, menej obchodov.
    volMult: float = 1.0
    #: Hranice od max / min(open, včerajšie zavretie) — zdroj. Vypnuté = od open.
    gapAdjust: bool = True
    # ---- ⏱️ Kontroly ------------------------------------------------------- #
    #: Vstupy aj výstupy sa rozhodujú len každých toľko minút od 9:30 (zdroj: 30 = 10:00, 10:30, …).
    checkEvery: int = 30
    #: Posledný vstup v minútach po 9:30 (360 = 15:30).
    lastEntryMin: int = 360
    #: Výstup aj pod VWAP — stop = max(horná hranica, VWAP), zdroj. Vypnuté = len hranica pásma.
    trailVwap: bool = True
    # ---- 🚪 Poistka, smer, počet ------------------------------------------- #
    #: Pevný stop u brokera v % z ceny vstupu, len poistka medzi kontrolami (zdroj ho nemá). 0 = 10 %.
    hardStopPct: float = 1.0
    tradeDirection: TradeDirection = TradeDirection.BOTH
    #: Strop vstupov za deň (zdroj ho nemá — po výstupe sa na ďalšej kontrole smie vstúpiť znova).
    maxTradesPerDay: int = 10
    weekdaysOnly: bool = True
    # ---- 💰 Veľkosť -------------------------------------------------------- #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showLevels: bool = True
    showVwap: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.lastEntryMin < self.checkEvery:
            yield f"lastEntryMin={self.lastEntryMin} je pred prvou kontrolou ({self.checkEvery} min po 9:30)"
