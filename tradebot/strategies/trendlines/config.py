"""Config stratégie Trendline Breakout.

Stratégia nemá Pine predlohu — vznikla zo zápisu klasického postupu „trendovka cez pivoty →
prerazenie zatvorením → (retest) → pokračovanie" (docs/sources chýba zámerne, `pine_path=None`).

Trendovky sa kreslia na vlastnom TF (`lineTF`, 5m až 4h), ktorý si engine skladá z barov
grafu; prerazenie sa hľadá na grafe. Prahy sú v ATR alebo v percentách ceny, nie v bodoch,
aby sa stratégia dala porovnať naprieč trhmi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["TrendlineConfig", "AnchorMode", "LineSlope", "EntryMode", "SlMode",
           "TradeDirection", "LINE_TFS", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: TF, na ktorých sa smú kresliť trendovky (minúty) — od 5m vyššie.
LINE_TFS: tuple[str, ...] = ("5", "10", "15", "30", "60", "120", "240")


class AnchorMode(str, Enum):
    """Cez čo sa trendovka kreslí."""

    WICK = "wick"  # high/low — klasická trendovka cez knôty
    BODY = "body"  # telá sviečok — jeden dlhý knôt čiaru neposunie


class LineSlope(str, Enum):
    """Aké trendovky sa obchodujú."""

    CLASSIC = "classic"  # klesajúci odpor (prerazenie = long) a rastúca podpora (= short)
    ANY = "any"          # aj rastúci odpor a klesajúca podpora (prerazenie kanála)


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class EntryMode(str, Enum):
    """Ako sa vstupuje do prerazenia trendovky."""

    CLOSE = "close"                # hneď na zavretí sviečky za čiarou
    SECOND_CLOSE = "second_close"  # až druhé zavretie za čiarou za sebou
    RETEST = "retest"              # limitka na návrat k prerazenej čiare
    RETEST_CLOSE = "retest_close"  # dotyk čiary a zavretie späť v smere prerazenia


class SlMode(str, Enum):
    LINE = "line"                  # za prerazenú trendovku (jej hodnota v čase vstupu)
    BREAK_CANDLE = "break_candle"  # za extrém prerazovacej sviečky
    SWING = "swing"                # za extrém posledných `slLookback` barov grafu
    ATR = "atr"                    # násobok ATR od vstupu


SIZE_FIELDS: dict[str, SizeUnit] = {
    "touchTolAtr": "atr",
    "breakBufferAtr": "atr",
    "slBufferAtr": "atr",
    "slAtrMult": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "anchorMode": AnchorMode,
    "lineSlope": LineSlope,
    "tradeDirection": TradeDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "pivotLen": (1, 20),
    "maxPivots": (2, 20),
    "minTouches": (2, 6),
    "minAnchorGap": (1, 200),
    "lineMaxAgeBars": (5, 1000),
    "minSlopeAtr": (0.0, 5.0),
    "maxSlopeAtr": (0.0, 10.0),
    "retestMaxBars": (1, 100),
    "maxTradesPerDay": (1, 50),
    "minClosePosPct": (0, 100),
    "cooldownBars": (0, 100),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "slLookback": (1, 100),
    "rrRatio": (0.2, 10.0),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.1, 10.0),
    "maxHoldBars": (0, 1000),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class TrendlineConfig(StrategyConfig):
    """Trendline breakout — trendovky cez pivoty na vlastnom TF a ich prerazenie na grafe."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 📐 Trendovky ------------------------------------------------------ #
    lineTF: str = "15"
    pivotLen: int = 5
    anchorMode: AnchorMode = AnchorMode.WICK
    lineSlope: LineSlope = LineSlope.CLASSIC
    maxPivots: int = 6
    minTouches: int = 2
    touchTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.2, "atr"))
    minAnchorGap: int = 5
    lineMaxAgeBars: int = 60
    minSlopeAtr: float = 0.0
    maxSlopeAtr: float = 0.0
    # ---- 🚀 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.CLOSE
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    retestMaxBars: int = 10
    minClosePosPct: int = 50
    maxTradesPerDay: int = 3
    cooldownBars: int = 3
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    slMode: SlMode = SlMode.LINE
    atrLen: int = 14
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.2, "atr"))
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    slLookback: int = 5
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    rrRatio: float = 1.5
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5
    maxHoldBars: int = 0
    closeAtWindowEnd: bool = False
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showLines: bool = True
    showPivots: bool = False
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    #: Doslovný Pine vzorec veľkosti pozície vrátane `int()` + `max(1, …)` — len na
    #: porovnanie s TradingView; pri qty < 1 sa riziko na obchod ticho neuplatní.
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def line_tf_minutes(self) -> int:
        return int(self.lineTF)

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
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if str(self.lineTF) not in LINE_TFS:
            yield f"lineTF={self.lineTF!r} musí byť jeden z {', '.join(LINE_TFS)} (minúty)"
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue (Pine ho v tom vzorci používa)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.maxSlopeAtr > 0 and self.maxSlopeAtr < self.minSlopeAtr:
            yield (f"maxSlopeAtr={self.maxSlopeAtr} musí byť aspoň minSlopeAtr={self.minSlopeAtr} "
                   "(0 = bez stropu)")
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield (f"obchodné okno: koniec ({self.tradeEndH}:{self.tradeEndM:02d}) musí byť "
                   f"za začiatkom ({self.tradeStartH}:{self.tradeStartM:02d})")
        if self.closeAtWindowEnd and not self.useTradeWindow:
            yield "closeAtWindowEnd nemá zmysel bez zapnutého obchodného okna (useTradeWindow)"
        if self.enableTrailing and self.trailOffsetR > self.trailActivationR:
            yield (f"trailOffsetR={self.trailOffsetR} > trailActivationR={self.trailActivationR}: "
                   "trailing by pri aktivácii posunul stop za vstup")
