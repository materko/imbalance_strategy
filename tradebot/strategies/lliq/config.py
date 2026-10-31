"""Config LONDON LIQUIDITY IFVG 1.0 — sweep high / low seansy a inverzný FVG (port `LondonSweepIfvg`, Shujat).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 2). Časy New York (HHMM).
  * **seansa** — high / low barov `sessionStart`–`sessionEnd` (predloha 13:00–19:00),
  * **sweep (LS)** — v okne `lsStart`–`lsEnd` zavretie za high (low) seansy a potom zavretie späť veľkým telom (> 50 %),
  * **IFVG** — FVG vznikajúce v seanse a po LS; FVG, ktoré cena zavretím prerazí proti jeho smeru (inverzia) v smere LS,
    v okne LS, je vstup: short po LS na high, long po LS na low, jeden za deň,
  * **stop** swing (`swingLookback` barov) alebo `slAtrMult` × ATR; **cieľ** range seansy, RR alebo `tpAtrMult` × ATR."""

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

__all__ = ["LliqConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'sessionStart': (0, 2359),
    'sessionEnd': (0, 2359),
    'lsStart': (0, 2359),
    'lsEnd': (0, 2359),
    'maxIfvgAgeHours': (1, 168),
    'swingLookback': (1, 50),
    'slType': (0, 1),
    'tpType': (0, 2),
    'riskReward': (0.1, 10.0),
    'atrLength': (1, 100),
    'slAtrMult': (0.1, 10.0),
    'tpAtrMult': (0.1, 10.0),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class LliqConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config LONDON LIQUIDITY IFVG 1.0 — sweep high / low seansy a inverzný FVG (port `LondonSweepIfvg`, Shujat)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕘 Seansa a sweep (New York, HHMM) ------------------------------------- #
    sessionStart: int = 1300
    sessionEnd: int = 1900
    lsStart: int = 1915
    lsEnd: int = 2345
    maxIfvgAgeHours: int = 24
    useDayFilter: bool = False
    tradeMon: bool = True
    tradeTue: bool = True
    tradeWed: bool = True
    tradeThu: bool = True
    tradeFri: bool = True
    # ---- 🛡️ Stop a cieľ -------------------------------------------------------- #
    swingLookback: int = 5
    slType: int = 1
    tpType: int = 2
    riskReward: float = 2.0
    atrLength: int = 14
    slAtrMult: float = 1.5
    tpAtrMult: float = 1.5
    fixedQty: bool = True
    riskDollar: float = 100.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        for name in ('sessionStart', 'sessionEnd', 'lsStart', 'lsEnd'):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
