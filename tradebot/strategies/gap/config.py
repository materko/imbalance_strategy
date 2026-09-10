"""Config stratégie Gap Fill — obchodovanie výplne otváracej medzery.

Prahy veľkosti medzery sú v **ATR**, nie v cenových bodoch: „100 bodov" znamená na NAS100
niečo úplne iné než na ropе, a meranie, z ktorého stratégia vychádza, je tiež v násobkoch
ATR (tiny gap = pod 0,3 ATR). Vďaka tomu sa dá ten istý profil pustiť na inom trhu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["GapConfig", "EntryMode", "SlMode", "TpMode", "GapDirection", "CONFIG_DIR"]

#: Profily stratégie ležia pri nej, aby bol balík sebestačný.
CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class GapDirection(str, Enum):
    """Ktoré medzery sa obchodujú."""

    BOTH = "Both"
    GAP_UP = "Gap up only"      # otvorenie nad včerajším close -> short na výplň
    GAP_DOWN = "Gap down only"  # otvorenie pod včerajším close -> long na výplň


class EntryMode(str, Enum):
    """Kedy sa vstupuje do výplne."""

    OPEN = "open"        # hneď na prvom bare seansy
    CONFIRM = "confirm"  # až keď prvá sviečka potvrdenia zavrie smerom k výplni
    RETEST = "retest"    # po potvrdení sa čaká na návrat k otváracej cene


class SlMode(str, Enum):
    """Kam ide stop."""

    ATR = "atr"            # násobok ATR za otváraciu cenu
    GAP_MULT = "gap_mult"  # násobok veľkosti medzery za otváraciu cenu
    OPEN_BAR = "open_bar"  # za extrém prvého baru seansy


class TpMode(str, Enum):
    """Kde je cieľ."""

    GAP = "gap"  # podiel medzery (100 % = celá výplň na včerajší close)
    RR = "rr"    # násobok vzdialenosti SL
    ATR = "atr"  # násobok ATR


SIZE_FIELDS: dict[str, SizeUnit] = {
    "minGapAtr": "atr",
    "maxGapAtr": "atr",
    "slAtrMult": "atr",
    "tpAtrMult": "atr",
}

ENUM_FIELDS: dict[str, type] = {
    "gapDirection": GapDirection,
    "entryMode": EntryMode,
    "slMode": SlMode,
    "tpMode": TpMode,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sessionStartH": (0, 23),
    "sessionStartM": (0, 59),
    "sessionEndH": (0, 23),
    "sessionEndM": (0, 59),
    "minGapAtr": (0.0, 5.0),
    "maxGapAtr": (0.05, 10.0),
    "confirmMinutes": (1, 120),
    "retestMaxBars": (1, 100),
    "entryWindowMinutes": (0, 480),
    "targetPct": (10, 200),
    "slAtrMult": (0.1, 10.0),
    "slGapMult": (0.2, 10.0),
    "tpAtrMult": (0.1, 20.0),
    "rrRatio": (0.3, 10.0),
    "maxHoldMinutes": (0, 480),
    "trailActivationR": (0.1, 10.0),
    "trailOffsetR": (0.1, 10.0),
    "atrLen": (2, 100),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage"})


@dataclass
class GapConfig(StrategyConfig):
    """Defaulty vychádzajú z merania na 2 791 dňoch NQ (2015–2025) — viď docs/ANALYTIKA.md."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🕐 Seansa -------------------------------------------------------- #
    sessionTZ: str = "America/New_York"
    sessionStartH: int = 9
    sessionStartM: int = 30
    sessionEndH: int = 15
    sessionEndM: int = 55
    weekdaysOnly: bool = True
    # ---- 📏 Medzera ------------------------------------------------------- #
    #: Pod 0,3 ATR („tiny gap") sa medzera vypĺňa v 77,8 % dní; nad 1,2 ATR len v 8,2 %.
    minGapAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    maxGapAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.30, "atr"))
    requireInsideRange: bool = True
    gapDirection: GapDirection = GapDirection.BOTH
    # ---- 🚪 Vstup --------------------------------------------------------- #
    entryMode: EntryMode = EntryMode.CONFIRM
    confirmMinutes: int = 15
    retestMaxBars: int = 10
    entryWindowMinutes: int = 60
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    tpMode: TpMode = TpMode.GAP
    targetPct: int = 100
    rrRatio: float = 1.0
    tpAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    slMode: SlMode = SlMode.ATR
    atrLen: int = 14
    #: Meranie: pohyb proti sebe má medián 0,34 ATR a 90. percentil 0,97 ATR.
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    slGapMult: float = 1.5
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    #: Medián času do výplne je 18 minút, 90. percentil 207. 0 = bez limitu.
    maxHoldMinutes: int = 120
    closeAtSessionEnd: bool = True
    enableTrailing: bool = False
    trailActivationR: float = 1.0
    trailOffsetR: float = 0.5
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showGap: bool = True
    showTarget: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    @property
    def trade_gap_up(self) -> bool:
        return self.gapDirection is not GapDirection.GAP_DOWN

    @property
    def trade_gap_down(self) -> bool:
        return self.gapDirection is not GapDirection.GAP_UP

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.maxGapAtr.value <= self.minGapAtr.value:
            yield (f"maxGapAtr={self.maxGapAtr.value} musí byť väčšie než "
                   f"minGapAtr={self.minGapAtr.value}, inak neprejde žiadna medzera")
        start = self.sessionStartH * 60 + self.sessionStartM
        end = self.sessionEndH * 60 + self.sessionEndM
        if end <= start:
            yield (f"koniec seansy {self.sessionEndH}:{self.sessionEndM:02d} musí byť "
                   f"za otvorením {self.sessionStartH}:{self.sessionStartM:02d}")
