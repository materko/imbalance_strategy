"""Config stratégie ORB — 34 vstupov z `tradebot/strategies/orb/docs/sources/orb.pine`.

Názvy polí sú zhodné s Pine identifikátormi, rovnako ako pri IBS a demo_breakout.
`tickDollarValue` a `leverage` sú rozšírenia portu, Pine ich nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["ORBConfig", "EntryMode", "RangeLength", "SessionMode", "SlMode", "TpMode",
           "TradeDirection", "SessionWindow", "CONFIG_DIR"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class RangeLength(str, Enum):
    """Dĺžka opening rangu v minútach — tri bežné varianty ORB."""

    M15 = "15"
    M30 = "30"
    M60 = "60"

    @property
    def minutes(self) -> int:
        return int(self.value)


class SessionMode(str, Enum):
    """Ktoré seansy sa obchodujú."""

    BOTH = "both"       # New York aj Londýn
    NY = "ny"           # len New York open
    LONDON = "london"   # len Londýn open


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


class EntryMode(str, Enum):
    """Ako sa vstupuje do prerazenia."""

    CLOSE = "close"           # vstup na zavretí sviečky za hranicou
    RETEST = "retest"         # limitka na návrat k prerazenej hranici
    STOP = "stop"             # agresívny stop order priamo na hranici


class SlMode(str, Enum):
    OPPOSITE = "opposite"          # opačná hrana rangu (= 100 % výšky)
    MID = "mid"                    # stred rangu (= 50 % výšky)
    RANGE_PCT = "range_pct"        # do rangu o nastavené % jeho výšky
    ATR = "atr"                    # násobok ATR od vstupu
    BREAK_CANDLE = "break_candle"  # za low/high prerazovacej sviečky


class TpMode(str, Enum):
    RR = "rr"              # násobok vzdialenosti SL
    MEASURED = "measured"  # výška rangu premietnutá za prerazenie
    ATR = "atr"            # násobok ATR


SIZE_FIELDS: dict[str, SizeUnit] = {
    "minSlDistance": "pct",
    "breakBufferAtr": "atr",
    "slAtrMult": "atr",
    "slBufferAtr": "atr",
    "tpAtrMult": "atr",
}

ENUM_FIELDS: dict[str, type] = {
    "sessionMode": SessionMode,
    "nyRangeMinutes": RangeLength,
    "lonRangeMinutes": RangeLength,
    "tradeDirection": TradeDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
    "tpMode": TpMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "nyStartH": (0, 23),
    "nyStartM": (0, 59),
    "nyEndH": (0, 23),
    "nyEndM": (0, 59),
    "lonStartH": (0, 23),
    "lonStartM": (0, 59),
    "lonEndH": (0, 23),
    "lonEndM": (0, 59),
    "breakBufferAtr": (0.0, 2.0),
    "retestMaxBars": (1, 100),
    "entryWindowMinutes": (0, 480),
    "maxTradesPerDay": (1, 20),
    "minRangePct": (0.0, 5.0),
    "maxRangePct": (0.1, 10.0),
    "volSmaLen": (2, 200),
    "volMultiplier": (0.5, 10.0),
    "minClosePosPct": (0, 100),
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

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass(frozen=True)
class SessionWindow:
    """Jedna obchodná seansa: kedy sa otvára, ako dlho stavia range a kedy končí.

    Minúty sú od polnoci v **pásme seansy**, nie v UTC — preto si každá nesie svoje `tz`.
    """

    key: str
    title: str
    tz: str
    start_minutes: int
    range_minutes: int
    end_minutes: int

    @property
    def range_end_minutes(self) -> int:
        return self.start_minutes + self.range_minutes


@dataclass
class ORBConfig(StrategyConfig):
    """Defaulty = Pine defaulty."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🕐 Seansy -------------------------------------------------------- #
    sessionMode: SessionMode = SessionMode.BOTH
    nyStartH: int = 9
    nyStartM: int = 30
    nyRangeMinutes: RangeLength = RangeLength.M15
    nyEndH: int = 15
    nyEndM: int = 55
    lonStartH: int = 8
    lonStartM: int = 0
    lonRangeMinutes: RangeLength = RangeLength.M15
    lonEndH: int = 16
    lonEndM: int = 30
    # ---- 🚀 Vstup --------------------------------------------------------- #
    tradeDirection: TradeDirection = TradeDirection.BOTH
    entryMode: EntryMode = EntryMode.CLOSE
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    retestMaxBars: int = 10
    entryWindowMinutes: int = 90
    maxTradesPerDay: int = 1
    # ---- 🚦 Filtre -------------------------------------------------------- #
    minRangePct: float = 0.15
    maxRangePct: float = 1.5
    useVolumeFilter: bool = False
    volSmaLen: int = 20
    volMultiplier: float = 1.5
    minClosePosPct: int = 50
    weekdaysOnly: bool = True
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
    closeAtSessionEnd: bool = True
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showRange: bool = True
    showLevels: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Hodnota jedného ticku v dolároch — CFD/futures nástroje ju potrebujú na sizing.
    tickDollarValue: float | None = None
    #: Doslovný Pine vzorec veľkosti pozície vrátane `int()` + `max(1, …)`. Zapnúť LEN
    #: na porovnanie s TradingView — pri qty < 1 sa riziko na obchod ticho neuplatní.
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. Poplatok je percento
    #: z nominálu a zisk rastie s R, takže obchody s tesným SL majú najhorší pomer
    #: edge k poplatku. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    #: Páka vo Freqtrade futures — Pine ju nemá.
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def sessions(self) -> tuple[SessionWindow, ...]:
        """Zapnuté seansy podľa `sessionMode`, každá s vlastným pásmom a oknom."""
        ny = SessionWindow(
            key="ny", title="New York", tz="America/New_York",
            start_minutes=self.nyStartH * 60 + self.nyStartM,
            range_minutes=self.nyRangeMinutes.minutes,
            end_minutes=self.nyEndH * 60 + self.nyEndM,
        )
        london = SessionWindow(
            key="london", title="Londýn", tz="Europe/London",
            start_minutes=self.lonStartH * 60 + self.lonStartM,
            range_minutes=self.lonRangeMinutes.minutes,
            end_minutes=self.lonEndH * 60 + self.lonEndM,
        )
        if self.sessionMode is SessionMode.NY:
            return (ny,)
        if self.sessionMode is SessionMode.LONDON:
            return (london,)
        return (ny, london)

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        """Veľkosť pozície — jediné miesto, kde sa rozhoduje medzi Pine a opraveným vzorcom."""
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue "\
                  "(Pine ho v tom vzorci používa)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.maxRangePct <= self.minRangePct:
            yield (f"maxRangePct={self.maxRangePct} musí byť väčšie než "
                   f"minRangePct={self.minRangePct}, inak neprejde žiadny range")
        for s in self.sessions:
            if s.end_minutes <= s.start_minutes:
                yield (f"{s.title}: koniec seansy musí byť za otvorením "
                       f"({s.end_minutes // 60}:{s.end_minutes % 60:02d} <= "
                       f"{s.start_minutes // 60}:{s.start_minutes % 60:02d})")
            elif s.start_minutes + s.range_minutes >= s.end_minutes:
                yield (f"{s.title}: opening range ({s.range_minutes} min) skončí až za koncom "
                       f"seansy — na obchodovanie by nezostal čas")
