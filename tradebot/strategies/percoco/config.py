"""Config stratégie Craig Percoco 1.0 — štruktúra trhu a momentum (CHoCH + FVG).

Podľa videa Craiga Percoca „This Boring Strategy Made Me $53,478 In A Month"
(https://www.youtube.com/watch?v=kngWJvQNrgQ, prečítané 8. 10. 2026):

  * **15m — smer a body záujmu**: trend zo štruktúry (zavretie nad posledný swing high = rast, pod
    posledný swing low = pokles; BOS pokračuje, CHoCH otáča) a nevyplnené FVG v smere trendu, do
    ktorých sa cena po impulze vracia,
  * **1m — vstup od otvorenia NY 9:30**: (1) CHoCH na 1m v smere 15m trendu, (2) FVG, ktoré vzniklo
    v pohybe CHoCH, (3) limitka na jeho stred (50 %), stop pod posledné low pohybu (pri shorte nad high),
    cieľ pevne 1:3 až 1:4 — „nastav a nechaj bežať", bez posunu stopu a bez čiastočných výstupov.

Čiaru cez lowy z videa nahrádza posledný potvrdený swing na 15m. Graf je 1m, 15m sa skladá z neho.
Stratégia nemá Pine predlohu.
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

__all__ = ["PercocoConfig", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "htfFvgMinAtr": "atr",
    "fvgMinAtr": "atr",
    "slBufferAtr": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {"tradeDirection": TradeDirection}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "htfTF": (2, 1440),
    "htfSwingLen": (1, 10),
    "htfFvgMaxBars": (1, 5000),
    "poiBars": (1, 2000),
    "swingLen": (1, 10),
    "entryPct": (0, 100),
    "setupMaxBars": (1, 2000),
    "rrRatio": (0.2, 20.0),
    "maxTradesPerDay": (1, 50),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class PercocoConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """15m trend a FVG ako body záujmu, 1m CHoCH + FVG, limitka na stred FVG, pevný cieľ v R."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🧭 15m: smer a body záujmu ---------------------------------------- #
    htfTF: int = 15
    #: Swing na 15m: pivot potvrdený toľkými sviečkami z každej strany.
    htfSwingLen: int = 2
    #: Obchodovať len v smere 15m trendu.
    useHtfBias: bool = True
    #: CHoCH musí prísť po dotyku nevyplneného 15m FVG v smere trendu (bod záujmu).
    useHtfPoi: bool = True
    htfFvgMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: 15m FVG platí najviac toľko 15m sviečok (288 = 3 dni).
    htfFvgMaxBars: int = 288
    #: Od dotyku 15m FVG po CHoCH na grafe najviac toľko sviečok grafu.
    poiBars: int = 60
    # ---- 🎯 1m vstup ------------------------------------------------------ #
    #: Swing na grafe (1m) pre CHoCH.
    swingLen: int = 2
    fvgMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Kde vo FVG je limitka: 50 = stred (video), 0 = bližšia hrana, 100 = vzdialenejšia.
    entryPct: int = 50
    #: Setup (limitka) platí najviac toľko sviečok grafu od CHoCH.
    setupMaxBars: int = 60
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 2
    # ---- 🚦 Okno obchodovania --------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = True
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 12
    tradeEndM: int = 0
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    #: Rezerva za low / high pohybu CHoCH.
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Cieľ = toľkokrát riziko (video 1:3 až 1:4).
    rrRatio: float = 4.0
    atrLen: int = 14
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showHtfFvg: bool = True
    showStructure: bool = True
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

    @property
    def window_start_minutes(self) -> int:
        return self.tradeStartH * 60 + self.tradeStartM

    @property
    def window_end_minutes(self) -> int:
        return self.tradeEndH * 60 + self.tradeEndM

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
