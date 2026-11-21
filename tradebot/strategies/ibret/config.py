"""Config IB RETRACE 1.0 — vstup na návrate do Initial Balance po prieraze, stop za úrovňou max retracementu.

Podľa videa IB Lab „Max Retracement Price“ (20. 11. 2026): po prieraze IB (9:30–10:30 NY) sa cena v ~70 % dní
nevráti hlbšie než istý zlomok IB (long pondelok −0,60 až −0,69, short utorok −0,70 až −0,79, single break).
Úrovne sú zlomky šírky IB od prerazenej hrany: 0 = hrana, 0,5 = stred IB, 1 = druhá strana IB.
Čísla zo štatistiky ešte prídu — defaulty sú zatiaľ z videa a ladia sa podľa nich.

  * **IB** — high / low barov s otvorením `ibStart` ≤ t < `ibStart` + `ibMinutes` (New York),
  * **prieraz** — `breakOn` wick (IB Lab): prvý bar po IB, ktorého knôt je ostro za IB (oba okraje v jednom bare =
    short); close: prvé zavretie baru za IB; otvorenie baru v okne `breakFrom`–`breakTo`, inak deň bez
    obchodu (rozhoduje vždy prvý prieraz dňa), deň v týždni podľa `tradeMon`…`tradeFri`,
  * **vstup** — `entryMode` pullback: limitka na úrovni `entryRetr` (návrat do IB), breakout: market na zavretí,
  * **stop** — úroveň `slRetr` (za max retracementom) − `slBufferTicks`; **cieľ** — extenzia `tpExt` × IB za
    prerazenou hranou alebo `rr` × stop; obchod s RR pod `minRR` sa vynechá,
  * **zrušenie limitky** — `lastEntry`, cena prerazí druhú stranu IB, alebo dôjde do cieľa bez návratu,
  * **koniec** — `closeAtEnd`: pozícia sa zavrie na zavretí baru o `exitTime`.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from tradebot.core.types import SizeUnit

__all__ = ["IbRetConfig", "BreakOn", "BiasFilter", "EntryMode", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryMode(str, Enum):
    PULLBACK = "pullback"    # limitka na úrovni entryRetr po prieraze
    BREAKOUT = "breakout"    # market na zavretí sviečky prierazu


class BreakOn(str, Enum):
    WICK = "wick"      # knôt ostro za IB (IB Lab, video); oba okraje v jednom bare = medvedí
    CLOSE = "close"    # zavretie baru za IB
    BODY = "body"      # celé telo baru za IB (otvorenie aj zavretie)


class BiasFilter(str, Enum):
    OFF = "off"
    WITH = "with"         # long len pri biase lowFirst (IB low vzniklo skôr ako high), short pri highFirst
    AGAINST = "against"   # naopak


class TpMode(str, Enum):
    EXT = "ext"    # extenzia tpExt × IB za prerazenou hranou
    RR = "rr"      # rr × vzdialenosť stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"breakOn": BreakOn, "biasFilter": BiasFilter, "entryMode": EntryMode, "tpMode": TpMode, "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "ibStart": (0, 2359), "ibMinutes": (5, 240), "breakFrom": (0, 2359), "breakTo": (0, 2359), "lastEntry": (0, 2359),
    "exitTime": (0, 2359), "entryRetr": (0.0, 0.95), "slRetr": (0.05, 1.5), "slBufferTicks": (0, 200),
    "tpExt": (0.05, 5.0), "rr": (0.5, 10.0), "shortEntryRetr": (0.0, 0.95), "shortSlRetr": (0.05, 1.5),
    "shortTpExt": (0.05, 5.0), "shortRr": (0.5, 10.0), "minRR": (0.0, 10.0), "minIbPoints": (0, 100000),
    "maxIbPoints": (0, 100000), "minIbPct": (0.0, 20.0), "maxIbPct": (0.0, 20.0), "ibAvgDays": (1, 250),
    "minIbRel": (0.0, 10.0), "maxIbRel": (0.0, 10.0), "qty": (0.001, 1000), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class IbRetConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Prieraz IB → vstup na návrate do IB, stop za úrovňou max retracementu, cieľ na extenzii IB."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕘 Initial Balance a prieraz (New York, HHMM) ----------------------- #
    ibStart: int = 930
    ibMinutes: int = 60
    #: Prieraz sa počíta, keď sa bar, ktorý zavrel za IB, otvoril v tomto okne (IB Lab: 10:30, 10:35, …).
    #: Čo je prieraz: knôt za IB (IB Lab) alebo zavretie za IB.
    breakOn: BreakOn = BreakOn.WICK
    breakFrom: int = 1030
    breakTo: int = 1125
    tradeMon: bool = True
    tradeTue: bool = True
    tradeWed: bool = True
    tradeThu: bool = True
    tradeFri: bool = True
    #: Šírka IB v bodoch (0 = bez hranice) — deň s užším / širším IB sa neobchoduje.
    minIbPoints: float = 0.0
    maxIbPoints: float = 0.0
    #: Šírka IB v % ceny (IB Lab „IB %“: (high − low) / stred × 100), 0 = bez hranice.
    minIbPct: float = 0.0
    maxIbPct: float = 0.0
    #: Šírka IB voči priemeru IB z `ibAvgDays` predošlých dní (1 = bežný deň), 0 = bez hranice.
    ibAvgDays: int = 20
    minIbRel: float = 0.0
    maxIbRel: float = 0.0
    #: Bias IB (IB Lab): lowFirst = IB low vzniklo skôr ako high (býčí). with = obchod len v smere biasu.
    biasFilter: BiasFilter = BiasFilter.OFF
    tradeDirection: TradeDirection = TradeDirection.BOTH
    # ---- 🎯 Vstup a úrovne (zlomok šírky IB od prerazenej hrany) ------------ #
    entryMode: EntryMode = EntryMode.PULLBACK
    #: Limitka: 0 = hrana IB, 0,25 = štvrtina IB späť dovnútra.
    entryRetr: float = 0.25
    #: Stop: úroveň max retracementu (video: 70 % dní long ≤ 0,69, short ≤ 0,79).
    slRetr: float = 0.8
    slBufferTicks: int = 0
    #: Limitka čaká najviac do tohto času (video: medián času max retracementu 13:30).
    lastEntry: int = 1330
    # ---- 🛡️ Cieľ a koniec ------------------------------------------------------ #
    tpMode: TpMode = TpMode.EXT
    #: Extenzia za prerazenou hranou (video: medián max extenzie +0,59 IB).
    tpExt: float = 0.5
    rr: float = 1.0
    #: Obchod s menším pomerom cieľ / stop sa vynechá (pravidlo testovania: nie pod 0,5).
    minRR: float = 0.5
    #: Short má vlastné úrovne (štatistika IB Lab: long a short sa vracajú inak hlboko); vypnuté = ako long.
    shortLevels: bool = False
    shortEntryRetr: float = 0.25
    shortSlRetr: float = 0.8
    shortTpExt: float = 0.5
    shortRr: float = 1.0
    closeAtEnd: bool = True
    exitTime: int = 1600
    # ---- 💰 Veľkosť ------------------------------------------------------------- #
    fixedQty: bool = False
    qty: float = 1.0
    riskDollar: float = 250.0
    # ---- 🎨 Vizualizácia --------------------------------------------------------- #
    drawRange: bool = True
    # ---- rozšírenia portu --------------------------------------------------------- #
    leverage: float = 1.0

    def levels(self, long: bool) -> tuple[float, float, float, float]:
        """(entryRetr, slRetr, tpExt, rr) pre smer obchodu."""
        if long or not self.shortLevels:
            return float(self.entryRetr), float(self.slRetr), float(self.tpExt), float(self.rr)
        return float(self.shortEntryRetr), float(self.shortSlRetr), float(self.shortTpExt), float(self.shortRr)

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        for name in ("ibStart", "breakFrom", "breakTo", "lastEntry", "exitTime"):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if float(self.slRetr) <= float(self.entryRetr):
            yield f"slRetr={self.slRetr} musí byť hlbšie než entryRetr={self.entryRetr}"
        if self.shortLevels and float(self.shortSlRetr) <= float(self.shortEntryRetr):
            yield f"shortSlRetr={self.shortSlRetr} musí byť hlbšie než shortEntryRetr={self.shortEntryRetr}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
