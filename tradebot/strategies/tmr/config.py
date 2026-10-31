"""Config T-MEAN REVERSION 1.0 — po červenom piatku long v pondelok, výstup v stredu (port Rust `TMeanReversion`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 3). Všetky časy UTC ako v predlohe, deň 1 = pondelok … 7 = nedeľa.
  * **piatok** — denná sviečka (kalendárny deň UTC) piatku zavrela pod svojím otvorením = červený piatok,
  * **vstup** — v deň `entryDay` na prvom bare s hodinou `entryHour` a minútou ≥ `entryMinute`, raz za deň,
    bez pozície, len po červenom piatku: long trhom,
  * **výstup** — v deň `exitDay` na prvom bare s hodinou `exitHour` a minútou ≥ `exitMinute`: zavrieť,
  * predloha nemá stop ani cieľ; `stopPct` je poistka portu (0 = 10 % od vstupu)."""

from __future__ import annotations

from dataclasses import dataclass
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

__all__ = ["TmrConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'entryDay': (1, 7),
    'entryHour': (0, 23),
    'entryMinute': (0, 59),
    'exitDay': (1, 7),
    'exitHour': (0, 23),
    'exitMinute': (0, 59),
    'marketOpenHour': (0, 23),
    'marketCloseHour': (0, 23),
    'stopPct': (0.0, 50.0),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class TmrConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config T-MEAN REVERSION 1.0 — po červenom piatku long v pondelok, výstup v stredu (port Rust `TMeanReversion`)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📅 Vstup a výstup (UTC, 1 = pondelok) ---------------------------------- #
    entryDay: int = 1
    entryHour: int = 17
    entryMinute: int = 0
    exitDay: int = 3
    exitHour: int = 20
    exitMinute: int = 0
    requireRedFriday: bool = True
    checkMarketHours: bool = False
    marketOpenHour: int = 1
    marketCloseHour: int = 23
    # ---- 🛡️ Poistka a veľkosť -------------------------------------------------- #
    stopPct: float = 0.0
    fixedQty: bool = True
    riskDollar: float = 500.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
