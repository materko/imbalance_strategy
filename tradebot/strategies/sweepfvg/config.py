"""Config stratégie SWEEP FVG 1.0 — výber likvidity → CHoCH / BOS → limitka na okraji najbližšieho FVG.

Stratégia nemá Pine predlohu; pravidlá zadal používateľ (10. 10. 2026, s nákresom):

  1. **likvidita** — výrazné swing vrcholy (buy-side) a dná (sell-side) na zapnutých TF (5m až 4h, skladajú sa
     z barov grafu); rovnaké vrcholy / dná sa zlúčia (rovnaké pravidlo ako stratégia Liquidity),
  2. **výber likvidity** — cena úroveň prerazí (knôt stačí; `sweepReclaim` = musí zavrieť späť),
  3. **CHoCH alebo BOS** v protismere do `breakMaxBars` barov: sviečka zavrie (alebo knôtom prejde, `breakBy`)
     za posledný swing grafu pred extrémom výberu (swing low pri výbere buy-side → short). CHoCH = zlom proti
     doterajšiemu smeru štruktúry, BOS = v jeho smere (`breakType`),
  4. **FVG** — najbližší signifikantný (aspoň `fvgMinAtr` ATR) nevyplnený FVG v smere obchodu, ktorý vznikol
     v pohybe od extrému výberu po zlom (alebo do `fvgWaitBars` barov po ňom),
  5. **vstup** limitkou na okraji FVG (`entryLevel` edge; voliteľne stred), čaká sa najviac `entryMaxBars` barov,
  6. **SL** nad extrém výberu (+ `slBufferAtr`), **TP** nastaviteľné: RR, body alebo najbližšia likvidita.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["SweepFvgConfig", "BreakBy", "BreakType", "EntryModel", "FvgPick", "TpMode", "TradeDirection",
           "LIQ_TIMEFRAMES", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: TF, na ktorých sa likvidita značí — pole configu -> minúty.
LIQ_TIMEFRAMES: tuple[tuple[str, int], ...] = (
    ("liqUse5m", 5), ("liqUse15m", 15), ("liqUse30m", 30), ("liqUse60m", 60), ("liqUse240m", 240),
)


class BreakBy(str, Enum):
    CLOSE = "close"   # sviečka zavrie za swingom
    WICK = "wick"     # stačí knôt


class BreakType(str, Enum):
    ANY = "any"       # CHoCH aj BOS
    CHOCH = "choch"   # len zlom proti doterajšiemu smeru štruktúry
    BOS = "bos"       # len zlom v smere štruktúry


class EntryModel(str, Enum):
    EDGE = "edge"     # limitka na okraji FVG, ku ktorému sa cena vracia (proximal)
    MID = "mid"       # limitka na strede FVG (consequent encroachment)


class FvgPick(str, Enum):
    NEAREST = "nearest"   # najbližšie k cene pri zlome
    LARGEST = "largest"   # najväčší
    FIRST = "first"       # prvý po výbere (najbližšie k extrému)


class TpMode(str, Enum):
    RR = "rr"                 # násobok stopu
    POINTS = "points"         # pevná vzdialenosť v bodoch ceny
    LIQUIDITY = "liquidity"   # najbližšia nevybratá likvidita v smere obchodu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "liqMinDispAtr": "atr", "liqEqualTolAtr": "atr", "fvgMinAtr": "atr", "slBufferAtr": "atr",
    "tpPoints": "abs", "maxSlAtr": "atr",
}
ENUM_FIELDS: dict[str, type] = {"breakBy": BreakBy, "breakType": BreakType, "entryLevel": EntryModel,
                                "fvgPick": FvgPick, "tpMode": TpMode, "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "liqPivotLen": (1, 30), "liqMaxAgeHours": (1, 2000), "liqMinStrength": (1, 5), "structPivotLen": (1, 20),
    "breakMaxBars": (1, 500), "fvgWaitBars": (0, 50), "entryMaxBars": (1, 500), "maxTradesPerDay": (1, 50),
    "startH": (0, 23), "startM": (0, 59), "endH": (0, 23), "endM": (0, 59), "exitH": (0, 23), "exitM": (0, 59),
    "rrRatio": (0.2, 20.0), "minRR": (0.0, 20.0), "atrLen": (2, 100), "riskDollar": (0, 100000),
    "qty": (0.001, 1000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class SweepFvgConfig(StrategyConfig, EntryFilterFields):
    """Výber likvidity → CHoCH / BOS → limitka na okraji najbližšieho FVG, SL za výber."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_FILTER_FIELD_NAMES

    # ---- 💧 Likvidita ---------------------------------------------------------- #
    liqUse5m: bool = False
    liqUse15m: bool = True
    liqUse30m: bool = False
    liqUse60m: bool = True
    liqUse240m: bool = False
    liqPivotLen: int = 5
    liqMinDispAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    liqEqualTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.15, "atr"))
    liqMaxAgeHours: int = 72
    liqMinStrength: int = 1
    #: Výber = cena úroveň prerazí; pri zapnutí musí sviečka výberu zavrieť späť pred úroveň.
    sweepReclaim: bool = False
    # ---- 🔀 CHoCH / BOS --------------------------------------------------------- #
    #: Swing grafu (pre zlom štruktúry): barov z každej strany.
    structPivotLen: int = 3
    breakBy: BreakBy = BreakBy.CLOSE
    breakType: BreakType = BreakType.ANY
    #: Do koľkých barov po výbere musí prísť zlom.
    breakMaxBars: int = 30
    # ---- 🟪 FVG a vstup ------------------------------------------------------- #
    #: Signifikantný FVG: medzera aspoň toľko ATR grafu.
    fvgMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.3, "atr"))
    fvgPick: FvgPick = FvgPick.NEAREST
    #: FVG smie vzniknúť aj toľko barov po zlome (sviečka zlomu býva stredom FVG).
    fvgWaitBars: int = 2
    entryLevel: EntryModel = EntryModel.EDGE
    #: Koľko barov po zlome čaká limitka na vyplnenie.
    entryMaxBars: int = 20
    maxTradesPerDay: int = 3
    tradeDirection: TradeDirection = TradeDirection.BOTH
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    #: Okno vstupov (čas New York).
    startH: int = 9
    startM: int = 30
    endH: int = 16
    endM: int = 0
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------- #
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    #: Širší stop ako toľko ATR = bez obchodu (0 = vypnuté).
    maxSlAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 2.0
    tpPoints: SizeSpec = field(default_factory=lambda: SizeSpec(50.0, "abs"))
    #: Pri cieli na likviditu: bližšia likvidita ako `minRR` × stop sa preskočí.
    minRR: float = 1.0
    atrLen: int = 14
    useExitTime: bool = False
    exitH: int = 15
    exitM: int = 55
    # ---- 💰 Veľkosť ------------------------------------------------------------ #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------- #
    showLevels: bool = True
    showStructure: bool = True
    showFvg: bool = True
    # ---- rozšírenia portu ------------------------------------------------------ #
    leverage: float = 1.0

    def active_liq_timeframes(self) -> tuple[int, ...]:
        return tuple(m for name, m in LIQ_TIMEFRAMES if getattr(self, name))

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def window(self) -> tuple[int, int]:
        return self.startH * 60 + self.startM, self.endH * 60 + self.endM

    @property
    def exit_minutes(self) -> int:
        return self.exitH * 60 + self.exitM

    def _problems(self) -> Iterable[str]:
        if not self.active_liq_timeframes():
            yield "nie je zapnutý žiadny TF likvidity (liqUse5m … liqUse240m)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        start, end = self.window
        if self.useTradeWindow and end <= start:
            yield "okno vstupov: koniec musí byť po začiatku"
