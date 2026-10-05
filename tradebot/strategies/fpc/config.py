"""Config stratégie FPC 1.0 — férová cena (Fair Pricing Theory podľa JJ Simona).

Podľa rozhovoru Chart Fanatics s JJ Simonom (5. 10. 2026), NQ futures na 1m grafe:

  * **férová cena** = otváracia cena prvej sviečky obchodného okna (NY 9:30, NY 14:00, Ázia, Londýn);
    v deň plánovanej správy o 8:30 je to cena pred správou (správa je „v cene", prvý pohyb je neférový),
  * **okná** = prvých 90 minút seansy, vstupy len vnútri okna,
  * **1. obchod okna — pokračovanie**: smer prvej sviečky, vstup na prieraz štruktúry v prvých minútach,
    v súlade s vyšším biasom (opak pohybu za posledných 6–12 h); 38 / 25 bodov, pri otváracej sviečke
    nad 25 bodov 76 / 50 (polovica kontraktov — pri riziku v dolároch to vyjde samo),
  * **ďalšie obchody — návrat k férovej cene**: nad ňou short, pod ňou long, vstup na displacement
    (telo väčšie ako predošlé + zavretie za knôt sviečky opačnej farby) alebo prieraz štruktúry
    (zavretie za posledný swing knôt); cieľ aspoň 80 % cesty k férovej cene,
  * **3 straty po sebe** v okne → koniec okna.

Video hovorí v bodoch NQ; stop a cieľ sú preto v bodoch ceny (`abs`). Pine predloha je mimo repozitára.
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

__all__ = ["FpcConfig", "NewsMode", "PmFair", "TpMode", "TradeDirection", "CONFIG_DIR", "WINDOWS"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: Obchodné okná: (číslo, názov). Pole okna k = useS{k}, s{k}H, s{k}M, s{k}Len.
WINDOWS: tuple[tuple[int, str], ...] = ((1, "NY ráno"), (2, "NY poobede"), (3, "Ázia"), (4, "Londýn"))


class NewsMode(str, Enum):
    OFF = "off"        # férová cena NY ráno je vždy open 9:30
    AUTO = "auto"      # cena pred správou, keď sviečka správy skočí (rozsah ≥ newsMult × priemer)
    ALWAYS = "always"  # cena pred časom správy každý deň


class PmFair(str, Enum):
    OPEN = "open"        # open poobedného okna
    MORNING = "morning"  # férová cena z rána (video: „keď 14:00 otvorí dole, vraciam to k 9:30")


class TpMode(str, Enum):
    FIXED = "fixed"  # pevné body (eval účty: 38)
    FAIR = "fair"    # cieľ priamo na férovej cene


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "contTP": "abs",
    "contSL": "abs",
    "bigBar": "abs",
    "revTP": "abs",
    "revSL": "abs",
    "minDist": "abs",
    "trendPts": "abs",
    "maxDist": "abs",
    "testTol": "abs",
}

ENUM_FIELDS: dict[str, type] = {
    "newsMode": NewsMode,
    "pmFair": PmFair,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    **{f"s{k}H": (0, 23) for k, _ in WINDOWS},
    **{f"s{k}M": (0, 59) for k, _ in WINDOWS},
    **{f"s{k}Len": (1, 720) for k, _ in WINDOWS},
    "newsH": (0, 23),
    "newsM": (0, 59),
    "newsMult": (1.0, 20.0),
    "newsAvgBars": (5, 500),
    "contWin": (1, 90),
    "biasH": (1, 24),
    "minPct": (0.0, 200.0),
    "pivLen": (1, 5),
    "maxLossRow": (1, 20),
    "maxTrades": (1, 100),
    "closeAfter": (0, 600),
    "pauseMin": (1, 240),
    "revDelay": (1, 240),
    "minTests": (1, 20),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class FpcConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Férová cena = open okna (v deň správy cena pred ňou); pokračovanie prvej sviečky a návraty k férovej cene."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 🕘 Obchodné okná (čas New York) ---------------------------------- #
    useS1: bool = True
    s1H: int = 9
    s1M: int = 30
    s1Len: int = 90
    useS2: bool = True
    s2H: int = 14
    s2M: int = 0
    s2Len: int = 90
    useS3: bool = False
    s3H: int = 20
    s3M: int = 0
    s3Len: int = 90
    useS4: bool = False
    s4H: int = 3
    s4M: int = 0
    s4Len: int = 90
    pmFair: PmFair = PmFair.OPEN
    # ---- 📰 Správa o 8:30 -------------------------------------------------- #
    newsMode: NewsMode = NewsMode.AUTO
    newsH: int = 8
    newsM: int = 30
    newsMult: float = 3.0
    newsAvgBars: int = 60
    #: Obchodovať návrat k cene pred správou hneď po nej (do začiatku okna NY ráno).
    useNewsWin: bool = True
    # ---- ➡️ 1. obchod: pokračovanie ---------------------------------------- #
    useCont: bool = True
    contWin: int = 5
    useBias: bool = True
    biasH: int = 8
    contTP: SizeSpec = field(default_factory=lambda: SizeSpec(38.0, "abs"))
    contSL: SizeSpec = field(default_factory=lambda: SizeSpec(25.0, "abs"))
    #: Otváracia sviečka väčšia než toto: TP aj SL × 2 (pri riziku v $ = polovica kontraktov).
    bigBar: SizeSpec = field(default_factory=lambda: SizeSpec(25.0, "abs"))
    # ---- ↩️ Návrat k férovej cene ----------------------------------------- #
    useRev: bool = True
    tpMode: TpMode = TpMode.FIXED
    revTP: SizeSpec = field(default_factory=lambda: SizeSpec(38.0, "abs"))
    revSL: SizeSpec = field(default_factory=lambda: SizeSpec(25.0, "abs"))
    #: Pri pevnom cieli: k férovej cene musí byť aspoň toľko % z TP (video: 80 %).
    minPct: float = 80.0
    #: Pri cieli na férovej cene: min. vzdialenosť k nej.
    minDist: SizeSpec = field(default_factory=lambda: SizeSpec(25.0, "abs"))
    # ---- 🎯 Vstupný signál a riadenie --------------------------------------- #
    useDisp: bool = True
    useBos: bool = True
    pivLen: int = 1
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxLossRow: int = 3
    maxTrades: int = 10
    useCloseAfter: bool = True
    closeAfter: int = 30
    # ---- 🚦 Filtre (každý sa zapína zvlášť) --------------------------------- #
    useTrend: bool = False
    trendPts: SizeSpec = field(default_factory=lambda: SizeSpec(20.0, "abs"))
    useMaxD: bool = False
    maxDist: SizeSpec = field(default_factory=lambda: SizeSpec(150.0, "abs"))
    usePause: bool = False
    pauseMin: int = 10
    useRevDel: bool = False
    revDelay: int = 10
    useTests: bool = False
    minTests: int = 2
    testTol: SizeSpec = field(default_factory=lambda: SizeSpec(3.0, "abs"))
    useRevBias: bool = False
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showFair: bool = True
    showZone: bool = True
    showSignals: bool = True
    showVwap: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def window(self, k: int) -> tuple[bool, int, int]:
        """(zapnuté, začiatok v minútach dňa NY, dĺžka v minútach) okna k."""
        on, h, m, length = {
            1: (self.useS1, self.s1H, self.s1M, self.s1Len),
            2: (self.useS2, self.s2H, self.s2M, self.s2Len),
            3: (self.useS3, self.s3H, self.s3M, self.s3Len),
            4: (self.useS4, self.s4H, self.s4M, self.s4Len),
        }[k]
        return bool(on), int(h) * 60 + int(m), int(length)

    @property
    def news_minutes(self) -> int:
        return self.newsH * 60 + self.newsM

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        for name in ("contTP", "contSL", "revTP", "revSL"):
            if getattr(self, name).value <= 0:
                yield f"{name} musí byť > 0"
        if not (self.useDisp or self.useBos):
            yield "zapni aspoň jeden vstupný signál (useDisp alebo useBos)"
        if self.useNewsWin and self.newsMode is not NewsMode.OFF and self.useS1:
            _, start, _ = self.window(1)
            if not self.news_minutes < start:
                yield "čas správy musí byť pred začiatkom okna NY ráno"
