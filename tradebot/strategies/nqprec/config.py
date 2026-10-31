"""Config NQ PRECISION 1.0 — OR 9:30–9:45 NY, snímka 9:59:55, filtre RVOL a režim ATR (port `NqPrecisionBot`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 5). Predloha beží na tickoch; port na 1m sviečkach: snímka
`triggerTime` = zavretie baru, ktorý končí v čase spúšte alebo po ňom (9:59:55 → zavretie 9:59 = 10:00).
  * **OR** — high / low barov `rangeStart` ≤ t < `rangeEnd` (HHMM, New York),
  * **vstup** — pri `useTriggerTime` jediná snímka: zavretie nad OR long, pod OR short, vnútri nič (deň končí);
    bez snímky prvý prieraz do `tradeUntil`; filtre RVOL (objem / priemer `rvolLen` barov dňa) a ATR(`atrPeriod`) /
    ATR(`atrRegimeLen`) v pásmach,
  * **stop / cieľ** — `atrSlMult` / `atrTpMult` × ATR, výstup po `closeAfterMin` minútach."""

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

__all__ = ["NqprecConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'rangeStart': (0, 2359),
    'rangeEnd': (0, 2359),
    'triggerTime': (0, 2359),
    'tradeUntil': (0, 2359),
    'rvolLen': (2, 200),
    'rvolMin': (0.0, 10.0),
    'rvolMax': (0.0, 20.0),
    'atrRegimeLen': (2, 400),
    'regimeMin': (0.0, 10.0),
    'regimeMax': (0.0, 20.0),
    'atrPeriod': (2, 100),
    'atrSlMult': (0.1, 10.0),
    'atrTpMult': (0.1, 10.0),
    'closeAfterMin': (1, 240),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class NqprecConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config NQ PRECISION 1.0 — OR 9:30–9:45 NY, snímka 9:59:55, filtre RVOL a režim ATR (port `NqPrecisionBot`)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕘 Range a spúšť (New York, HHMM) -------------------------------------- #
    rangeStart: int = 930
    rangeEnd: int = 945
    useTriggerTime: bool = True
    triggerTime: int = 1000
    tradeUntil: int = 1100
    # ---- 📏 Filtre -------------------------------------------------------------- #
    useFilters: bool = True
    rvolLen: int = 14
    rvolMin: float = 0.5
    rvolMax: float = 1.5
    atrRegimeLen: int = 50
    regimeMin: float = 1.0
    regimeMax: float = 2.5
    # ---- 🛡️ Stop, cieľ a čas --------------------------------------------------- #
    atrPeriod: int = 14
    atrSlMult: float = 2.2
    atrTpMult: float = 0.3
    useTimeClose: bool = True
    closeAfterMin: int = 8
    fixedQty: bool = True
    riskDollar: float = 500.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        for name in ('rangeStart', 'rangeEnd', 'triggerTime', 'tradeUntil'):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
