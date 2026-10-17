"""Config stratégie Silver Bullet 1.0 (ICT) — okno 10:00–11:00 NY, výber likvidity, FVG, limitka.

Stratégia nemá Pine predlohu; pravidlá podľa ICT Silver Bullet (zadanie používateľa 17. 10. 2026, obrázok
„ICT SILVER BULLET — 1 10–11 AM · 2 SWEEP · 3 FVG“):

  1. **okno** — všetko sa deje v čase New York `sbStartH:sbStartM`–`sbEndH:sbEndM` (default 10:00–11:00),
  2. **likvidita** — skoršie vrcholy a dná dňa: high / low úseku od `liqFromH:liqFromM` po začiatok okna a swingy
     grafu (`liqPivotLen`) od `liqFromH:liqFromM`, ktoré ešte cena nevybrala,
  3. **sweep** — v okne cena knôtom prerazí skoršie dno (sell-side) → čaká sa na long, vrchol (buy-side) → short;
     `sweepReclaim` = sviečka musí zavrieť späť za úroveň,
  4. **FVG** — po sweepe prudký pohyb opačným smerom: medzera medzi 1. a 3. sviečkou v smere obchodu, aspoň
     `fvgMinAtr` ATR, vzniknutá do `fvgMaxBars` barov po extréme sweepu (voliteľne aj zlom štruktúry, `requireMss`),
  5. **vstup** — limitka na okraji FVG (`entryLevel` edge, voliteľne stred) alebo market na zavretí sviečky, ktorá
     FVG vytvorila (`entryType`); platí do konca okna,
  6. **SL** za extrém sweepu (+ `slBufferAtr`), **TP** na protiľahlej likvidite (skorší vrchol / dno, aspoň `minRR`)
     alebo `rrRatio` × stop.
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
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["SilverBulletConfig", "EntryLevel", "EntryType", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryLevel(str, Enum):
    EDGE = "edge"     # okraj FVG, ku ktorému sa cena vracia (proximal)
    MID = "mid"       # stred FVG (consequent encroachment)


class EntryType(str, Enum):
    LIMIT = "limit"   # limitka na FVG (ICT)
    MARKET = "market"  # market na zavretí sviečky, ktorá FVG vytvorila (dá sa potvrdiť IBS imbalance / pin bar)


class TpMode(str, Enum):
    LIQUIDITY = "liquidity"   # protiľahlá likvidita — skorší vrchol (long) / dno (short), aspoň minRR
    RR = "rr"                 # násobok stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {"fvgMinAtr": "atr", "slBufferAtr": "atr", "maxSlAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {"entryLevel": EntryLevel, "entryType": EntryType, "tpMode": TpMode,
                                "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sbStartH": (0, 23), "sbStartM": (0, 59), "sbEndH": (0, 23), "sbEndM": (0, 59),
    "liqFromH": (0, 23), "liqFromM": (0, 59), "liqPivotLen": (1, 20), "fvgMaxBars": (1, 100), "structPivotLen": (1, 20),
    "maxTradesPerDay": (1, 10), "rrRatio": (0.2, 20.0), "minRR": (0.0, 20.0), "atrLen": (2, 100),
    "exitH": (0, 23), "exitM": (0, 59), "riskDollar": (0, 100000), "qty": (0.001, 1000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class SilverBulletConfig(StrategyConfig, EntryConfirmFields, EntryFilterFields):
    """ICT Silver Bullet: okno 10–11 NY, výber likvidity, FVG v protismere, limitka na FVG."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS,
                                                              **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕙 Okno ------------------------------------------------------------- #
    #: Začiatok okna (New York). Sweep, FVG aj vstup musia prísť v okne. ICT: 10:00.
    sbStartH: int = 10
    sbStartM: int = 0
    #: Koniec okna (New York). Nevyplnená limitka sa na konci zruší. ICT: 11:00.
    sbEndH: int = 11
    sbEndM: int = 0
    # ---- 💧 Likvidita ---------------------------------------------------------- #
    #: Odkedy sa berú skoršie vrcholy a dná dňa (New York). 8:00 = od otvorenia „pre-market“ obchodovania.
    liqFromH: int = 8
    liqFromM: int = 0
    #: High / low celého úseku od `liqFrom` po začiatok okna je likvidita.
    useRangeHL: bool = True
    #: Swingy grafu od `liqFrom` sú likvidita (vrchol / dno o `liqPivotLen` barov z každej strany).
    useSwings: bool = True
    liqPivotLen: int = 3
    #: Sweep platí, len keď sviečka zavrie späť za úroveň (inak stačí knôt).
    sweepReclaim: bool = False
    # ---- 🟪 FVG a vstup ---------------------------------------------------------- #
    #: Minimálna medzera FVG v ATR.
    fvgMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    #: FVG musí vzniknúť do toľkých barov po extréme sweepu.
    fvgMaxBars: int = 10
    #: Navyše zlom štruktúry (MSS): zavretie za posledný swing grafu pred extrémom sweepu.
    requireMss: bool = False
    structPivotLen: int = 2
    entryLevel: EntryLevel = EntryLevel.EDGE
    entryType: EntryType = EntryType.LIMIT
    maxTradesPerDay: int = 1
    tradeDirection: TradeDirection = TradeDirection.BOTH
    weekdaysOnly: bool = True
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------------ #
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    #: Najväčší stop v ATR (0 = bez stropu) — príliš veľký sweep sa neobchoduje.
    maxSlAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    tpMode: TpMode = TpMode.LIQUIDITY
    rrRatio: float = 2.0
    #: Pri cieli na likvidite: najbližšia protiľahlá likvidita aspoň toľko R od vstupu.
    minRR: float = 1.0
    atrLen: int = 14
    #: Výstup v čase (nie je súčasť ICT pravidiel; default vypnuté — len stop a cieľ).
    useExitTime: bool = False
    exitH: int = 15
    exitM: int = 55
    # ---- 💰 Veľkosť -------------------------------------------------------------- #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia --------------------------------------------------------- #
    showWindow: bool = True
    showLevels: bool = True
    showFvg: bool = True
    # ---- rozšírenia portu -------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def window(self) -> tuple[int, int]:
        return self.sbStartH * 60 + self.sbStartM, self.sbEndH * 60 + self.sbEndM

    @property
    def liq_from(self) -> int:
        return self.liqFromH * 60 + self.liqFromM

    @property
    def exit_minutes(self) -> int:
        return self.exitH * 60 + self.exitM

    def _problems(self) -> Iterable[str]:
        start, end = self.window
        if end <= start:
            yield "okno: koniec musí byť po začiatku"
        if self.liq_from >= start:
            yield "likvidita sa musí začať zbierať pred oknom (liqFrom < sbStart)"
        if not (self.useRangeHL or self.useSwings):
            yield "zapni aspoň jeden zdroj likvidity (useRangeHL alebo useSwings)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
