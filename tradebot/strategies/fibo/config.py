"""Config stratégie Fibo — návrat k Fibonacciho úrovniam po impulze a vstup na potvrdenie.

Podľa videa „This Fibonacci Trading Strategy…" (Brad Goh, The Trading Geek), 2. 10. 2026:

  1. jasný trend — impulz (noha) od swing dna po swing vrchol (v klesajúcom trende naopak),
  2. Fibonacci sa ťahá cez nohu po knôtoch: 0 % = koniec nohy, 100 % = jej začiatok;
     úrovne návratu 38,2 / 50 / 61,8 / 78,6 %, extenzie −27 % a −61,8 %,
  3. čaká sa na návrat k niektorej úrovni (úroveň je oblasť, nie presná cena); prerazenie
     100 % znamená, že to už nie je návrat — setup padá,
  4. nevstupuje sa na dotyk: treba znamenie, že návrat skončil (vo videu knôty, pohltenie,
     morning star; tu naše vstupné modely IBS imbalance a pin bar),
  5. stop za swing, cieľ na extenzii −27 %.

Swingy sa hľadajú na vlastnom TF (`swingTF`, skladá sa z barov grafu), vstupné modely bežia
na grafe — graf môže byť nižší TF. Je to hrubý základ pre väčšiu stratégiu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["FiboConfig", "LevelMode", "EntryModel", "SlMode", "TpMode", "TradeDirection", "FIB_LEVELS", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: Úrovne návratu: pole configu -> podiel nohy.
FIB_LEVELS: tuple[tuple[str, float], ...] = (("use382", 0.382), ("use50", 0.5), ("use618", 0.618), ("use786", 0.786))


class LevelMode(str, Enum):
    ZONE = "zone"      # kdekoľvek medzi najplytšou a najhlbšou zapnutou úrovňou
    LEVELS = "levels"  # dno návratu musí byť pri niektorej zapnutej úrovni (± tolerancia)


class EntryModel(str, Enum):
    IMBALANCE = "imbalance"  # IBS: imbalance sviečka (medzera medzi 1. a 3. sviečkou) v smere
    PINBAR = "pinbar"        # pin bar — dlhý knôt proti smeru
    ANY = "any"              # imbalance alebo pin bar


class SlMode(str, Enum):
    LEG = "leg"            # za začiatok nohy (úroveň 100 %) — video
    PULLBACK = "pullback"  # za extrém návratu (tesnejší stop)


class TpMode(str, Enum):
    EXTENSION = "extension"  # extenzia nohy (`tpExtensionPct`, video −27 %)
    RR = "rr"                # násobok stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "legMinAtr": "atr",
    "levelTolAtr": "atr",
    "imbMinSizeAtr": "atr",
    "slBufferAtr": "atr",
    "slBufferPoints": "abs",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "levelMode": LevelMode,
    "entryModel": EntryModel,
    "slMode": SlMode,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "swingTF": (1, 1440),
    "swingLen": (1, 30),
    "legMaxBars": (0, 2000),
    "setupMaxBars": (1, 5000),
    "signalMaxBars": (0, 100),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "atrLen": (2, 100),
    "tpExtensionPct": (-100.0, 500.0),
    "rrRatio": (0.2, 20.0),
    "minRR": (0.0, 20.0),
    "maxTradesPerDay": (1, 50),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "maxHoldBars": (0, 5000),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class FiboConfig(StrategyConfig, EntryOrderFields):
    """Impulz, návrat k Fibonacciho úrovniam a vstup na potvrdzovaciu sviečku."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES

    # ---- 📐 Noha (impulz) -------------------------------------------------- #
    swingTF: int = 15
    swingLen: int = 3
    #: Noha musí byť dlhá aspoň toľko ATR (TF swingov) — „jasný trend".
    legMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(3.0, "atr"))
    #: Koniec nohy musí prekonať predošlý swing v smere (vyšší vrchol / nižšie dno).
    requireBreak: bool = True
    #: Najviac toľko barov TF swingov od začiatku po koniec nohy (0 = bez limitu).
    legMaxBars: int = 0
    atrLen: int = 14
    # ---- 🔢 Úrovne návratu -------------------------------------------------- #
    use382: bool = True
    use50: bool = True
    use618: bool = True
    use786: bool = True
    levelMode: LevelMode = LevelMode.ZONE
    #: Úroveň je oblasť: o koľko ATR grafu smie byť dno návratu od úrovne (`levels`) alebo za okrajom zóny.
    levelTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.25, "atr"))
    #: Setup platí toľko barov TF swingov od potvrdenia nohy.
    setupMaxBars: int = 60
    # ---- 🎯 Vstup ---------------------------------------------------------- #
    entryModel: EntryModel = EntryModel.ANY
    #: Signál najviac toľko barov grafu po sviečke, ktorá spravila dno návratu (0 = bez limitu).
    signalMaxBars: int = 3
    imbMinSizeAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    pbWickPct: int = 60
    pbBodyPct: int = 30
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 3
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 3
    tradeStartM: int = 0
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slMode: SlMode = SlMode.LEG
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    slBufferPoints: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    tpMode: TpMode = TpMode.EXTENSION
    #: Extenzia za koniec nohy v % jej dĺžky: 27 = úroveň −27 %, 61.8 = −61,8 %, 0 = koniec nohy.
    tpExtensionPct: float = 27.0
    rrRatio: float = 2.0
    minRR: float = 0.5
    maxHoldBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showFibo: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    legacyPineSizing: bool = False
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

    def levels(self) -> tuple[float, ...]:
        """Zapnuté úrovne návratu (podiel nohy), vzostupne."""
        return tuple(v for name, v in FIB_LEVELS if getattr(self, name))

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
        if not self.levels():
            yield "nie je zapnutá žiadna úroveň návratu (use382 … use786)"
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.pbBodyPct + self.pbWickPct > 100:
            yield f"pbWickPct + pbBodyPct = {self.pbWickPct + self.pbBodyPct} > 100 — pin bar nemôže vzniknúť"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
