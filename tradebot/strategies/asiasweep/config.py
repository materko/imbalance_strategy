"""Config stratégie ASIA SWEEP 1.0 — londýnska seansa vyberie likviditu Ázie, obchod do protismeru.

Koncept (ICT / smart money): ázijská seansa vytvorí úzky range, nad jeho maximom a pod minimom ležia
stopky (likvidita). Londýnska seansa ich vyberie — cena prerazí maximum alebo minimum Ázie a vráti
sa späť do rangu — a potom ide do protismeru:

  * **range Ázie**: najvyššia a najnižšia cena sviečok v okne `asiaStart`–`asiaEnd` (čas New York,
    default 20:00–00:00),
  * **sweep**: v okne `sweepStart`–`sweepEnd` (Londýn, default 2:00–5:00) cena prerazí maximum
    (minimum) Ázie aspoň o `sweepMin`; pri `requireReclaim` musí potom sviečka zavrieť späť v range,
  * **vstup** do protismeru (po vybratí maxima short, po vybratí minima long) najneskôr `entryBars`
    sviečok po sweepe a do `entryEnd`: vstupný model IBS imbalance, pin bar, jeden z nich alebo len
    zavretie sviečky v smere,
  * **stop** za extrémom sweepu (+ rezerva v ATR), za signálnou sviečkou alebo v ATR; **cieľ**
    `rrRatio` × stop, opačná strana rangu Ázie, jeho stred alebo najbližší naked POC; voliteľne
    zatvorenie v čase,
  * **nPOC filter** (`useNpoc`, voliteľný): volume profile dňa (`vpStart`–`vpEnd`, default forexový deň
    17:00–17:00 NY) dá POC; kým ho cena po skončení dňa nedotkne, je „naked". Vstup len keď v smere
    obchodu (long nad cenou, short pod ňou) leží naked POC z posledných `npocDays` dní — trh tam má kam ísť.

Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["AsiaSweepConfig", "EntryModel", "SlMode", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryModel(str, Enum):
    IMBALANCE = "imbalance"  # IBS: medzera medzi 1. a 3. sviečkou v smere, stredná zavrela za 1.
    PINBAR = "pinbar"        # pin bar — dlhý knôt proti smeru (aj samotná sviečka sweepu)
    ANY = "any"              # imbalance alebo pin bar
    CLOSE = "close"          # hneď zavretie sviečky v smere (bez vzoru)


class SlMode(str, Enum):
    SWEEP = "sweep"    # za extrém sweepu + rezerva
    SIGNAL = "signal"  # za extrém signálnej sviečky (a dvoch pred ňou) + rezerva
    ATR = "atr"        # násobok ATR od vstupu


class TpMode(str, Enum):
    RR = "rr"          # rrRatio × vzdialenosť stopu
    RANGE = "range"    # opačná strana rangu Ázie
    MID = "mid"        # stred rangu Ázie
    NPOC = "npoc"      # najbližší naked POC v smere obchodu (bez neho cieľ RR)


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "sweepMin": "atr",
    "maxSweep": "atr",
    "rangeMinPct": "pct",
    "rangeMaxPct": "pct",
    "slBuffer": "atr",
    "slAtr": "atr",
    "imbMinSize": "atr",
}

ENUM_FIELDS: dict[str, type] = {
    "entryModel": EntryModel,
    "slMode": SlMode,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "asiaStartH": (0, 23), "asiaStartM": (0, 59), "asiaEndH": (0, 23), "asiaEndM": (0, 59),
    "sweepStartH": (0, 23), "sweepStartM": (0, 59), "sweepEndH": (0, 23), "sweepEndM": (0, 59),
    "entryEndH": (0, 23), "entryEndM": (0, 59),
    "vpStartH": (0, 23), "vpStartM": (0, 59), "vpEndH": (0, 23), "vpEndM": (0, 59),
    "vpRowTicks": (1, 100000), "npocDays": (1, 20),
    "exitH": (0, 23), "exitM": (0, 59),
    "entryBars": (1, 500),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "rrRatio": (0.2, 20.0),
    "maxTradesPerDay": (1, 4),
    "atrLen": (2, 100),
    "riskDollar": (0, 1_000_000),
    "qty": (0.001, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class AsiaSweepConfig(StrategyConfig, EntryOrderFields, EntryFilterFields):
    """Range Ázie, jeho vybratie v Londýne a vstup do protismeru vstupným modelom IBS / pin bar."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 🌏 Range Ázie (čas New York) -------------------------------------- #
    asiaStartH: int = 20
    asiaStartM: int = 0
    asiaEndH: int = 0
    asiaEndM: int = 0
    #: Filter veľkosti rangu (% z ceny); 0 = vypnuté.
    rangeMinPct: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    rangeMaxPct: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    # ---- 🇬🇧 Sweep v Londýne ------------------------------------------------- #
    sweepStartH: int = 2
    sweepStartM: int = 0
    sweepEndH: int = 5
    sweepEndM: int = 0
    #: O koľko musí cena prekročiť maximum / minimum Ázie (ATR grafu); 0 = stačí o tick.
    sweepMin: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Hlbší prieraz než toto (ATR) už nie je sweep, ale pokračovanie — setup padá. 0 = vypnuté.
    maxSweep: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Po prieraze musí sviečka zavrieť späť v range, až potom sa hľadá vstup.
    requireReclaim: bool = True
    # ---- 🎯 Vstup ---------------------------------------------------------- #
    entryModel: EntryModel = EntryModel.ANY
    imbMinSize: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    pbWickPct: int = 60
    pbBodyPct: int = 30
    #: Koľko sviečok po sweepe sa ešte hľadá vstup.
    entryBars: int = 12
    entryEndH: int = 8
    entryEndM: int = 0
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 1
    weekdaysOnly: bool = True
    # ---- 📊 Volume profile — naked POC (voliteľné) ------------------------- #
    #: Vstup len keď v smere obchodu leží naked POC (nedotknutý POC predošlého dňa).
    useNpoc: bool = False
    #: Z koľkých posledných dní sa naked POC berú (1 = len predošlý deň).
    npocDays: int = 1
    #: Deň profilu (čas New York); začiatok = koniec → celých 24 h od začiatku.
    vpStartH: int = 17
    vpStartM: int = 0
    vpEndH: int = 17
    vpEndM: int = 0
    #: Výška riadku profilu v tickoch (EURUSD: 10 tickov = 1 pip).
    vpRowTicks: int = 10
    # ---- 🛡️ Stop a cieľ ---------------------------------------------------- #
    slMode: SlMode = SlMode.SWEEP
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(0.2, "atr"))
    slAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    atrLen: int = 14
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 2.0
    useExitTime: bool = True
    exitH: int = 12
    exitM: int = 0
    # ---- 💰 Veľkosť -------------------------------------------------------- #
    fixedQty: bool = False
    qty: float = 1.0
    riskDollar: float = 1000.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showRange: bool = True
    showSweeps: bool = True
    showNpoc: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def asia_start(self) -> int:
        return self.asiaStartH * 60 + self.asiaStartM

    @property
    def asia_end(self) -> int:
        return self.asiaEndH * 60 + self.asiaEndM

    @property
    def sweep_start(self) -> int:
        return self.sweepStartH * 60 + self.sweepStartM

    @property
    def sweep_end(self) -> int:
        return self.sweepEndH * 60 + self.sweepEndM

    @property
    def entry_end(self) -> int:
        return self.entryEndH * 60 + self.entryEndM

    @property
    def vp_start(self) -> int:
        return self.vpStartH * 60 + self.vpStartM

    @property
    def vp_end(self) -> int:
        return self.vpEndH * 60 + self.vpEndM

    @property
    def exit_time(self) -> int:
        return self.exitH * 60 + self.exitM

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.asia_start == self.asia_end:
            yield "range Ázie: začiatok a koniec nesmú byť rovnaké"
        if self.sweep_start == self.sweep_end:
            yield "okno sweepu: začiatok a koniec nesmú byť rovnaké"
        if self.pbBodyPct + self.pbWickPct > 100:
            yield f"pbWickPct + pbBodyPct = {self.pbWickPct + self.pbBodyPct} > 100 — pin bar nemôže vzniknúť"
        if self.rangeMaxPct.value and self.rangeMaxPct.value <= self.rangeMinPct.value:
            yield "rangeMaxPct musí byť väčšie ako rangeMinPct"
