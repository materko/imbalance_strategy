"""Config WILLIAMS %R LONG 1.0 — %R pod −90 long, výstup nad high predošlej sviečky alebo %R ≥ −30 (port `WprLong`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 8, sama port Pine v6). Len long.
  * **vstup** — %R(`wprLen`) zavrie pod `entryLevel`, bez pozície; po obchode až keď %R najprv vystúpi na `entryLevel`,
  * **výstup** — `exitMode` 0: zavretie nad high predošlej sviečky, 1: %R ≥ `exitLevel`, 2: hociktoré,
  * predloha nemá stop; `stopPct` je poistka portu (0 = 10 % od vstupu)."""

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

__all__ = ["WprConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'wprLen': (1, 500),
    'entryLevel': (-100.0, 0.0),
    'exitLevel': (-100.0, 0.0),
    'exitMode': (0, 2),
    'stopPct': (0.0, 50.0),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class WprConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config WILLIAMS %R LONG 1.0 — %R pod −90 long, výstup nad high predošlej sviečky alebo %R ≥ −30 (port `WprLong`)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📉 Williams %R --------------------------------------------------------- #
    wprLen: int = 14
    entryLevel: float = -90.0
    exitLevel: float = -30.0
    exitMode: int = 2
    # ---- 🛡️ Poistka a veľkosť -------------------------------------------------- #
    stopPct: float = 0.0
    fixedQty: bool = True
    riskDollar: float = 500.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
