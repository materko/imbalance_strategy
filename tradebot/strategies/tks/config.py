"""Config stratégie TKS 1.0 — obchod podľa NQ Kompasu (trend dňa na Nasdaqu).

NQ Kompas 0–100 = priemer štyroch zložiek trendu dňa (seansa NY 9:30–16:00): únik zo šumu (pohyb od otvorenia
v násobkoch bežného pohybu pre tú minútu za `lookbackDays` dní), poloha v nočnom range, tlak (poloha zavretia
× objem od 9:30) a čas nad VWAP. Konštanty sú pevné (MNQ 2019-06 – 2025-09).

Pravidlá (zadanie používateľa, 18. 10. 2026): `nConf` sviečok po sebe zavrie s Kompasom pod `loLevel` → market
short, SL na najbližší swing high nad cenou, TP = `rrRatio` × SL; zrkadlovo nad `hiLevel` → long, SL najbližší
swing low. Nový signál až keď Kompas medzitým odíde od hranice; jedna pozícia naraz.
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

__all__ = ["TksConfig", "TradeDirection", "SlMode", "CONFIG_DIR", "PRESS_SCALE"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"
#: 90. percentil |tlak| na MNQ 1m 2019-06 – 2025-09 — škála zložky tlak (pevná, ako v Pine NQ Kompas)
PRESS_SCALE = 0.1293


class SlMode(str, Enum):
    SWING = "swing"      # najbližší swing high / low za cenou (zadanie)
    ATR = "atr"          # slAtrMult × ATR grafu od vstupu
    POINTS = "points"    # pevne slPoints bodov od vstupu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"tradeDirection": TradeDirection, "slMode": SlMode}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "lookbackDays": (5, 30), "loLevel": (5, 50), "hiLevel": (50, 95), "nConf": (1, 20), "rrRatio": (0.5, 10.0),
    "pivLen": (1, 20), "maxTradesPerSession": (0, 50), "qty": (0.001, 1000), "riskDollar": (0, 100000),
    "leverage": (1, 125), "entryStartMin": (0, 390), "entryEndMin": (0, 390), "pauseFromMin": (0, 390),
    "pauseToMin": (0, 390), "slAtrMult": (0.2, 10.0), "slPoints": (1, 1000), "maxSlPoints": (0, 1000), "maxSlAtr": (0, 20),
    "atrLen": (2, 100),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class TksConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Obchod podľa NQ Kompasu: N sviečok za hranicou → vstup v smere, SL na swing, TP v RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🧭 NQ Kompas ------------------------------------------------------ #
    #: Pásmo šumu (zložka „únik zo šumu“) z toľkých predošlých dní.
    lookbackDays: int = 14
    # ---- 🎯 Pravidlá ------------------------------------------------------- #
    #: Short, keď Kompas zavrie pod touto hranicou `nConf` sviečok po sebe.
    loLevel: float = 35.0
    #: Long, keď Kompas zavrie nad touto hranicou `nConf` sviečok po sebe.
    hiLevel: float = 65.0
    nConf: int = 3
    #: TP = RR × vzdialenosť SL.
    rrRatio: float = 1.0
    #: Swing high / low = vrchol / dno potvrdené toľkými sviečkami na každej strane.
    pivLen: int = 3
    # ---- ⏱️ Časové okno (minúty po 9:30 NY, podľa zavretia signálnej sviečky) ---- #
    #: Vstupy najskôr / najneskôr (0 / 390 = celá seansa; 60 = 10:30, 330 = 15:00).
    entryStartMin: int = 0
    entryEndMin: int = 390
    #: Prestávka bez vstupov, napr. obed 150–180 = 12:00–12:30 (rovnaké čísla = vypnuté).
    pauseFromMin: int = 0
    pauseToMin: int = 0
    # ---- 🛡️ Stop loss ------------------------------------------------------ #
    #: swing = najbližší swing za cenou (zadanie), atr = slAtrMult × ATR, points = slPoints bodov.
    slMode: SlMode = SlMode.SWING
    slAtrMult: float = 2.0
    slPoints: float = 40.0
    atrLen: int = 14
    #: Strop vzdialenosti SL — obchod so vzdialenejším SL sa vynechá (0 = bez stropu).
    maxSlPoints: float = 0.0
    maxSlAtr: float = 0.0
    #: Najviac vstupov za seansu 9:30–16:00 (0 = bez limitu).
    maxTradesPerSession: int = 0
    #: Zatvoriť pozíciu o 16:00 NY (pravidlá testovania: vypnuté).
    closeAtSessionEnd: bool = False
    tradeDirection: TradeDirection = TradeDirection.BOTH
    # ---- 💰 Veľkosť -------------------------------------------------------- #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.loLevel >= self.hiLevel:
            yield f"loLevel={self.loLevel} musí byť pod hiLevel={self.hiLevel}"
