"""Config stratégie Scalping 3MA + RSI + fraktál — obchod v smere trendu po potvrdení fraktálom.

Podľa videa „5 Minutová Scalping Stratégia" (kanál Money Knowledge, Rene), 2. 10. 2026:

  * tri vyhladené kĺzavé priemery (SMMA) 20, 60 a 200, RSI a Williamsove fraktály,
  * **trend**: sviečky pod všetkými troma priemermi = klesajúci (short), nad všetkými = rastúci (long);
    v bočnom trhu sa neobchoduje,
  * **RSI** pod 50 pre short, nad 50 pre long,
  * **fraktál** je potvrdenie vstupu,
  * stop 5 pipov, cieľ 10 pipov (1 : 2), posun stopu na vstup (break-even) a výstup, keď RSI
    prejde cez 50 proti obchodu; odporúčaný je jeden obchod denne.

Video ukazuje EURUSD a hovorí o pipoch; stop sa preto dá zadať v bodoch ceny (`points`),
v ATR (`atr`, prenosné medzi trhmi) alebo za fraktál (`fractal`).
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

__all__ = ["Scalp3MaConfig", "FractalSide", "SlMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class FractalSide(str, Enum):
    PULLBACK = "pullback"  # short: fraktál hore (vrchol pullbacku), long: fraktál dole — šípka indikátora v smere obchodu
    TREND = "trend"        # short: fraktál dole (nové dno), long: fraktál hore
    ANY = "any"            # ktorýkoľvek fraktál


class SlMode(str, Enum):
    POINTS = "points"    # pevná vzdialenosť v bodoch ceny (video: 5 pipov)
    ATR = "atr"          # násobok ATR
    FRACTAL = "fractal"  # za extrém fraktálu + rezerva


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "slPoints": "abs",
    "slAtr": "atr",
    "slBufferAtr": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "fractalSide": FractalSide,
    "slMode": SlMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "ma1Len": (2, 500),
    "ma2Len": (2, 500),
    "ma3Len": (2, 1000),
    "rsiLen": (2, 100),
    "rsiLevel": (1, 99),
    "fractalLen": (1, 10),
    "atrLen": (2, 100),
    "rrRatio": (0.2, 20.0),
    "beAtR": (0.0, 10.0),
    "maxTradesPerDay": (1, 100),
    "cooldownBars": (0, 500),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class Scalp3MaConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Trend podľa troch SMMA, RSI nad / pod 50, fraktál ako potvrdenie; stop a cieľ 1 : 2."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 📈 Trend (tri SMMA) --------------------------------------------- #
    ma1Len: int = 20
    ma2Len: int = 60
    ma3Len: int = 200
    #: Priemery musia byť aj zoradené (short: 20 < 60 < 200). Video to nevyžaduje.
    requireMaOrder: bool = False
    # ---- 📊 RSI ----------------------------------------------------------- #
    rsiLen: int = 14
    rsiLevel: float = 50.0
    #: Zavrieť obchod, keď RSI prejde cez úroveň proti nemu (video).
    rsiExit: bool = True
    # ---- 🔺 Fraktál a vstup ------------------------------------------------ #
    fractalLen: int = 2
    fractalSide: FractalSide = FractalSide.PULLBACK
    tradeDirection: TradeDirection = TradeDirection.BOTH
    #: Video odporúča jeden obchod denne (inak sa ľahko preobchoduje).
    maxTradesPerDay: int = 1
    cooldownBars: int = 0
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 3
    tradeStartM: int = 0
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slMode: SlMode = SlMode.ATR
    slPoints: SizeSpec = field(default_factory=lambda: SizeSpec(0.0005, "abs"))
    slAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    atrLen: int = 14
    rrRatio: float = 2.0
    #: Posun stopu na vstup po zisku toľkých R (video: „dať SL na BE"). 0 = vypnuté.
    beAtR: float = 1.0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showMa: bool = False
    showFractals: bool = True
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
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
        if not (self.ma1Len < self.ma2Len < self.ma3Len):
            yield "dĺžky priemerov musia rásť: ma1Len < ma2Len < ma3Len"
