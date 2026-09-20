"""Config stratégie Breakout — prerazenie prvej 5-minútovej sviečky New York open.

Stratégia nemá Pine predlohu (`pine_path=None`); vznikla zo zadania:
prvá 5-minútová sviečka otvorenia newyorskej seansy dá high a low, obchoduje sa
**zavretie** sviečky za tou hranicou a stop ide pod/nad tú istú sviečku.

Dve veci, ktoré určujú tvar configu:

* **Opening sviečka je 5-minútová, ale vstupuje sa na 1m/2m/3m grafe.** 5 sa dvomi ani
  tromi nedelí, takže z barov grafu sa tá sviečka poskladať nedá — 3m graf by dal okno
  9:30–9:36. Berie sa preto z informatívneho TF (`openingMinutes`), rovnako ako IBS
  berie detekčný TF zón. Na 1m, 2m aj 3m grafe je tak hranica presne tá istá.
* **Prahy sú v ATR alebo v percentách ceny**, nikdy v cenových bodoch — inak by sa
  rovnaký profil nedal porovnať na NAS100 a na BTC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["BreakoutConfig", "OpeningLength", "OrderKind", "TradeDirection", "CONFIG_DIR"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class OpeningLength(str, Enum):
    """Dĺžka otváracej sviečky v minútach.

    Hodnoty sú len tie, ktoré Tester naozaj má na disku (`tester/timeframes.json`) —
    informatívny TF sa z nich skladá menom (`"5m"`, `"15m"`).
    """

    M5 = "5"
    M15 = "15"

    @property
    def minutes(self) -> int:
        return int(self.value)

    @property
    def timeframe(self) -> str:
        return f"{self.value}m"


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class OrderKind(str, Enum):
    """Akým príkazom sa do prerazenia vstupuje.

    Oba vznikajú na tom istom signáli (zavretá sviečka za hranicou) a líšia sa len
    cenou plnenia — preto sa dajú porovnať jeden proti druhému:

    * ``market`` — hneď na zavretí prerazovacej sviečky; vstúpi sa vždy, ale horšie.
    * ``limit``  — limitka späť na prerazenú hranicu (retest); lepšia cena a kratší
      stop, ale časť prerazení sa nevráti a obchod nevznikne.
    """

    MARKET = "market"
    LIMIT = "limit"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "breakBufferAtr": "atr",
    "slBufferAtr": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "openingMinutes": OpeningLength,
    "tradeDirection": TradeDirection,
    "orderType": OrderKind,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sessionStartH": (0, 23),
    "sessionStartM": (0, 59),
    "sessionEndH": (0, 23),
    "sessionEndM": (0, 59),
    "breakBufferAtr": (0.0, 2.0),
    "limitValidMinutes": (1, 240),
    "entryWindowMinutes": (0, 480),
    "maxTradesPerDay": (1, 20),
    "minClosePosPct": (0, 100),
    "minRangePct": (0.0, 5.0),
    "maxRangePct": (0.1, 10.0),
    "volSmaLen": (2, 200),
    "volMultiplier": (0.5, 10.0),
    "atrLen": (2, 100),
    "slBufferAtr": (0.0, 2.0),
    "rrRatio": (0.5, 10.0),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.1, 10.0),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "legacyPineSizing", "minSlDistance", "leverage"})


@dataclass
class BreakoutConfig(StrategyConfig):
    """Parametre stratégie Breakout. Defaulty = zadanie (NY 9:30, 5 min, SL pod sviečku, 1:1)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🕐 Seansa -------------------------------------------------------- #
    #: Otvorenie newyorskej seansy v pásme America/New_York — 9:30 NY je 15:30 SEČ v zime
    #: a 15:30 SELČ v lete. Pásmo rieši prechod na letný čas samo, preto sa čas píše v NY.
    sessionStartH: int = 9
    sessionStartM: int = 30
    openingMinutes: OpeningLength = OpeningLength.M5
    sessionEndH: int = 15
    sessionEndM: int = 55
    weekdaysOnly: bool = True
    # ---- 🚀 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    orderType: OrderKind = OrderKind.MARKET
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    limitValidMinutes: int = 15
    entryWindowMinutes: int = 90
    maxTradesPerDay: int = 1
    minClosePosPct: int = 0
    # ---- 🚦 Filtre -------------------------------------------------------- #
    minRangePct: float = 0.0
    maxRangePct: float = 10.0
    useVolumeFilter: bool = False
    volSmaLen: int = 20
    volMultiplier: float = 1.5
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    atrLen: int = 14
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    rrRatio: float = 1.0
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5
    closeAtSessionEnd: bool = True
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showRange: bool = True
    showLevels: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Hodnota jedného ticku v dolároch — CFD a futures ju potrebujú na risk-based sizing.
    tickDollarValue: float | None = None
    #: Doslovný Pine vzorec veľkosti pozície (`int()` + `max(1, …)`). Len na porovnanie
    #: s TradingView; pri qty < 1 sa riziko na obchod ticho neuplatní.
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    #: Páka vo Freqtrade futures.
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def start_minutes(self) -> int:
        """Otvorenie seansy v minútach od polnoci New Yorku."""
        return self.sessionStartH * 60 + self.sessionStartM

    @property
    def end_minutes(self) -> int:
        return self.sessionEndH * 60 + self.sessionEndM

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue (Pine ho v tom vzorci používa)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.maxRangePct <= self.minRangePct:
            yield (f"maxRangePct={self.maxRangePct} musí byť väčšie než minRangePct="
                   f"{self.minRangePct}, inak neprejde ani jedna otváracia sviečka")
        if self.end_minutes <= self.start_minutes + self.openingMinutes.minutes:
            yield (f"koniec seansy {self.sessionEndH}:{self.sessionEndM:02d} je skôr než koniec "
                   f"otváracej sviečky — na prerazenie by nezostal ani jeden bar")
        if 0 < self.entryWindowMinutes <= self.openingMinutes.minutes:
            yield (f"okno na vstup ({self.entryWindowMinutes} min) skončí ešte pred koncom "
                   f"otváracej sviečky ({self.openingMinutes.minutes} min)")
