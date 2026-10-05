"""Config stratégie FVG POLARITY — obchod späť k práve vzniknutému FVG, cieľ je jeho dotyk.

Stratégia nemá Pine predlohu; vznikla zo zadania používateľa (1. 10. 2026, s nákresom):
na 15m grafe, keď vznikne FVG, najbližšia sviečka otvorí market obchod **k medzere** (po
medvedom FVG long, po býčom short), drží sa až po dotyk FVG — tam je TP — a stop je 20 bodov.

Stop a veľkosť FVG sú v **bodoch ceny** (`abs`), lebo tak ich zadal používateľ a obchoduje
MNQ; na inom trhu treba body prepočítať.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.entry_confirm import (ENTRY_CONFIRM_CONSTRAINTS, ENTRY_CONFIRM_ENUMS, ENTRY_CONFIRM_FIELD_NAMES,
                                         EntryConfirmFields)
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["FvgPolarityConfig", "TpLevel", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class TpLevel(str, Enum):
    """Kde v medzere je cieľ.

    * ``near`` — prvý dotyk FVG: bližšia hrana medzery (zadanie)
    * ``mid``  — stred medzery
    * ``far``  — vzdialenejšia hrana (medzera sa celá vyplní)
    """

    NEAR = "near"
    MID = "mid"
    FAR = "far"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "fvgMinSize": "abs",
    "fvgMaxSize": "abs",
    "slPoints": "abs",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {"tpLevel": TpLevel, "tradeDirection": TradeDirection}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "fvgMinSize": (0.0, 100000.0),
    "fvgMaxSize": (0.0, 100000.0),
    "slPoints": (0.0, 100000.0),
    "atrLen": (2, 100),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "legacyPineSizing", "minSlDistance", "leverage"})


@dataclass
class FvgPolarityConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Parametre FVG POLARITY. Defaulty = zadanie (15m, TP na dotyk FVG, SL 20 bodov)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 🟪 FVG ------------------------------------------------------------ #
    #: Najmenšia a najväčšia výška medzery v bodoch; 0 = bez obmedzenia.
    fvgMinSize: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    fvgMaxSize: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    # ---- 🚀 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slPoints: SizeSpec = field(default_factory=lambda: SizeSpec(20.0, "abs"))
    tpLevel: TpLevel = TpLevel.NEAR
    atrLen: int = 14
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showFvg: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    legacyPineSizing: bool = False
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.slPoints.value <= 0:
            yield "slPoints musí byť väčší než 0 — bez stopu nemá obchod riziko ani veľkosť"
        if self.fvgMaxSize.value > 0 and self.fvgMaxSize.value < self.fvgMinSize.value:
            yield (f"fvgMaxSize={self.fvgMaxSize.value} je menší než fvgMinSize={self.fvgMinSize.value} "
                   f"— neprejde žiadny FVG")
