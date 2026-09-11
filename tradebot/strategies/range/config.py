"""Config stratégie Range Breakout.

Stratégia nemá Pine predlohu — vznikla zo zápisu klasického postupu „konsolidácia →
prerazenie → pokračovanie" (docs/sources chýba zámerne, `pine_path=None`).

Všetky prahy sú v ATR alebo v percentách ceny, nie v cenových bodoch. Je to vedomé
rozhodnutie: range breakout má zmysel porovnávať naprieč trhmi a prah v bodoch by to
znemožnil (na NAS100 znamená 10 bodov niečo iné než na XAU alebo EURUSD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["RangeConfig", "BoundaryMode", "EntryMode", "SlMode", "TpMode",
           "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class BoundaryMode(str, Enum):
    """Z čoho sa berú hranice rangu."""

    CLOSE = "close"      # najvyšší/najnižší close — odolnejšie voči knôtom
    EXTREME = "extreme"  # high/low — klasické, ale citlivejšie na jeden dlhý knôt


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class EntryMode(str, Enum):
    """Ako sa vstupuje do prerazenia."""

    CLOSE = "close"                # hneď na zavretí sviečky za hranicou
    RETEST = "retest"              # limitka na návrat k prerazenej hranici
    CONTINUATION = "continuation"  # po retestte sa čaká na potvrdzujúci close v smere prerazenia


class SlMode(str, Enum):
    OPPOSITE = "opposite"          # opačná hrana rangu
    MID = "mid"                    # stred rangu
    RANGE_PCT = "range_pct"        # do rangu o nastavené % jeho výšky
    ATR = "atr"                    # násobok ATR od vstupu
    BREAK_CANDLE = "break_candle"  # za extrém prerazovacej sviečky


class TpMode(str, Enum):
    RR = "rr"              # násobok vzdialenosti SL
    MEASURED = "measured"  # výška rangu premietnutá za prerazenie
    ATR = "atr"            # násobok ATR


SIZE_FIELDS: dict[str, SizeUnit] = {
    "maxWidthAtr": "atr",
    "minWidthAtr": "atr",
    "breakBufferAtr": "atr",
    "slAtrMult": "atr",
    "slBufferAtr": "atr",
    "tpAtrMult": "atr",
}

ENUM_FIELDS: dict[str, type] = {
    "boundaryMode": BoundaryMode,
    "tradeDirection": TradeDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
    "tpMode": TpMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "lookbackBars": (4, 100),
    "maxWidthAtr": (0.2, 10.0),
    "minWidthAtr": (0.0, 5.0),
    "maxRangeAgeBars": (1, 200),
    "cooldownBars": (0, 100),
    "breakBufferAtr": (0.0, 2.0),
    "retestMaxBars": (1, 100),
    "confirmMaxBars": (1, 50),
    "maxTradesPerDay": (1, 20),
    "minClosePosPct": (0, 100),
    "maxHoldBars": (0, 500),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "slRangePct": (5.0, 150.0),
    "slAtrMult": (0.1, 10.0),
    "slBufferAtr": (0.0, 2.0),
    "rrRatio": (0.5, 10.0),
    "measuredMult": (0.2, 5.0),
    "tpAtrMult": (0.1, 20.0),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.1, 10.0),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage"})


@dataclass
class RangeConfig(StrategyConfig):
    """Range breakout — konsolidácia kdekoľvek na grafe, jej prerazenie a pokračovanie."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🔍 Detekcia rangu ------------------------------------------------ #
    lookbackBars: int = 15
    boundaryMode: BoundaryMode = BoundaryMode.CLOSE
    maxWidthAtr: SizeSpec = field(default_factory=lambda: SizeSpec(2.0, "atr"))
    minWidthAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.5, "atr"))
    maxRangeAgeBars: int = 40
    cooldownBars: int = 3
    # ---- 🚀 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.CLOSE
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    requireSecondClose: bool = False
    retestMaxBars: int = 10
    confirmMaxBars: int = 5
    maxTradesPerDay: int = 3
    minClosePosPct: int = 50
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    slMode: SlMode = SlMode.OPPOSITE
    slRangePct: float = 50.0
    atrLen: int = 14
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 1.5
    measuredMult: float = 1.0
    tpAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(2.0, "atr"))
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5
    maxHoldBars: int = 0
    closeAtWindowEnd: bool = False
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showRange: bool = True
    showLevels: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

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

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.minWidthAtr.value >= self.maxWidthAtr.value:
            yield (f"minWidthAtr={self.minWidthAtr.value} musí byť menšie než "
                   f"maxWidthAtr={self.maxWidthAtr.value}, inak neprejde žiadny range")
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield (f"obchodné okno: koniec ({self.tradeEndH}:{self.tradeEndM:02d}) musí byť "
                   f"za začiatkom ({self.tradeStartH}:{self.tradeStartM:02d})")
        if self.closeAtWindowEnd and not self.useTradeWindow:
            yield "closeAtWindowEnd nemá zmysel bez zapnutého obchodného okna (useTradeWindow)"
