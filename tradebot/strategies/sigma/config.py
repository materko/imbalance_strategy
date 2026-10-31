"""Config SIGMA BREAKOUT 1.0 — pásmo šumu z rovnakej minúty za N dní, prieraz zavretím, otáčanie (port `SigmaBreakout`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 4). RTH 9:30–16:00 New York.
  * **referencia** — open RTH alebo (`useVwap`) VWAP RTH k predošlému baru,
  * **sigma** — priemer |zavretie − open RTH| v tej istej minúte (HH:MM) za posledných `nSigmaDays` dní,
  * **vstup** — zavretie nad ref + `bandMult` × sigma long, pod ref − … short; opačný prieraz pozíciu otočí,
  * **koniec** — od 16:00 NY všetko von; stop `slPct` % (0 = bez stopu, poistka portu 10 %)."""

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

__all__ = ["SigmaConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'nSigmaDays': (2, 60),
    'bandMult': (0.1, 5.0),
    'slPct': (0.0, 20.0),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class SigmaConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config SIGMA BREAKOUT 1.0 — pásmo šumu z rovnakej minúty za N dní, prieraz zavretím, otáčanie (port `SigmaBreakout`)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📊 Pásmo --------------------------------------------------------------- #
    nSigmaDays: int = 14
    bandMult: float = 1.0
    useVwap: bool = False
    # ---- 🛡️ Stop a veľkosť ----------------------------------------------------- #
    slPct: float = 0.0
    useCloseAtEnd: bool = True
    fixedQty: bool = True
    riskDollar: float = 500.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
