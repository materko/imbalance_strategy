"""Config IB RETRACE 1.0 — vstup na návrate do Initial Balance po prieraze, stop za úrovňou max retracementu.

Podľa videa IB Lab „Max Retracement Price“ (20. 11. 2026): po prieraze IB (9:30–10:30 NY) sa cena v ~70 % dní
nevráti hlbšie než istý zlomok IB (long pondelok −0,60 až −0,69, short utorok −0,70 až −0,79, single break).
Úrovne sú zlomky šírky IB od prerazenej hrany: 0 = hrana, 0,5 = stred IB, 1 = druhá strana IB.
Čísla zo štatistiky ešte prídu — defaulty sú zatiaľ z videa a ladia sa podľa nich.

  * **IB** — high / low barov s otvorením `ibStart` ≤ t < `ibStart` + `ibMinutes` (New York),
  * **prieraz** — prvé zavretie baru za IB po jeho konci; otvorenie baru v okne `breakFrom`–`breakTo`, inak deň bez
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

__all__ = ["IbRetConfig", "EntryMode", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EntryMode(str, Enum):
    PULLBACK = "pullback"    # limitka na úrovni entryRetr po prieraze
    BREAKOUT = "breakout"    # market na zavretí sviečky prierazu


class TpMode(str, Enum):
    EXT = "ext"    # extenzia tpExt × IB za prerazenou hranou
    RR = "rr"      # rr × vzdialenosť stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"entryMode": EntryMode, "tpMode": TpMode, "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "ibStart": (0, 2359), "ibMinutes": (5, 240), "breakFrom": (0, 2359), "breakTo": (0, 2359), "lastEntry": (0, 2359),
    "exitTime": (0, 2359), "entryRetr": (0.0, 0.95), "slRetr": (0.05, 1.5), "slBufferTicks": (0, 200),
    "tpExt": (0.05, 5.0), "rr": (0.5, 10.0), "minRR": (0.0, 10.0), "minIbPoints": (0, 100000),
    "maxIbPoints": (0, 100000), "qty": (0.001, 1000), "riskDollar": (0, 100000), "leverage": (1, 125),
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
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
