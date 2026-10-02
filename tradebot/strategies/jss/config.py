"""Config stratégie JSS 1.0 — BOS / CHoCH, SD zóna, ktorá ho spôsobila, a vstup na jej hrane.

Stratégia nemá Pine predlohu; pravidlá zadal používateľ (29. 9. 2026):

  1. na TF štruktúry (`structTF`, default 4h, skladá sa z barov grafu) príde BOS alebo CHoCH —
     sviečka **zavrie** za posledným potvrdeným swingom,
  2. nájde sa najbližšia SD zóna, ktorá ten pohyb spôsobila (báza / posledná opačná sviečka
     pred impulzom na začiatku nohy, ktorá swing prerazila),
  2b. v tej zóne sa nájde zóna nižšieho TF (`refineTF`, default 15m) rovnakou definíciou —
     na nej je limitka (upresnenie vstupu, 30. 9. 2026),
  3. vstup pri návrate do zóny: limitka na hranu zóny, alebo po dotyku IBS imbalance /
     pin bar na grafe (nižší TF),
  4. SL za protiľahlú hranu zóny, cieľ RR, extrém nohy, ktorá BOS spravila, alebo jej Fibonacciho extenzia.
  5. voliteľne Fibonacci (`useFibo`): cez nohu BOS sa natiahne fibo a zóna sa obchoduje, len keď vstup
     leží v zadanom pásme návratu (napr. 50–100 % = „zľava").

Obchoduje sa len prvý dotyk zóny; nový BOS nahradí zónu starého. Prahy sú v ATR.
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
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                          EntryOrderFields)

__all__ = ["JssConfig", "TriggerMode", "ZoneType", "ZoneEdge", "EntryModel", "TpMode",
           "TradeDirection", "SlFrom", "STRUCT_TFS", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: TF štruktúry, ktoré sa dajú zvoliť (minúty).
STRUCT_TFS: tuple[int, ...] = (2, 3, 5, 10, 15, 30, 60)


class TriggerMode(str, Enum):
    BOS = "bos"      # len prerazenie v smere trendu
    CHOCH = "choch"  # len zmena charakteru (prvé prerazenie proti trendu)
    BOTH = "both"


class ZoneType(str, Enum):
    OB = "ob"      # posledná opačná sviečka pred impulzom (order block)
    BASE = "base"  # celá báza pred impulzom (až `baseMaxBars` sviečok od začiatku nohy)


class ZoneEdge(str, Enum):
    WICK = "wick"  # zóna od knôtu po knôt
    BODY = "body"  # bližšia hrana na tele (vstup hlbšie), vzdialená na knôte


class EntryModel(str, Enum):
    TOUCH = "touch"          # limitka na hranu zóny (dotyk)
    IMBALANCE = "imbalance"  # po dotyku IBS imbalance v smere na grafe
    PINBAR = "pinbar"        # po dotyku pin bar v smere
    ANY = "any"              # imbalance alebo pin bar


class SlFrom(str, Enum):
    REFINED = "refined"  # za upresnenú zónu nižšieho TF (tesnejší stop)
    HTF = "htf"          # za zónu TF štruktúry


class TpMode(str, Enum):
    RR = "rr"                # násobok stopu
    STRUCTURE = "structure"  # extrém nohy, ktorá BOS spravila (nové dno / vrchol)
    EXTENSION = "extension"  # Fibonacciho extenzia nohy BOS (`tpExtensionPct`, −27 %)


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "impulseAtr": "atr",
    "zoneMinAtr": "atr",
    "zoneMaxAtr": "atr",
    "imbMinSizeAtr": "atr",
    "slBufferAtr": "atr",
    "slBufferPoints": "abs",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "triggerMode": TriggerMode,
    "zoneType": ZoneType,
    "zoneEdge": ZoneEdge,
    "entryModel": EntryModel,
    "tpMode": TpMode,
    "slFrom": SlFrom,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "structTF": (1, 1440),
    "refineTF": (0, 240),
    "swingLen": (1, 30),
    "baseMaxBars": (1, 20),
    "zoneMaxAgeBars": (0, 5000),
    "entryDepthPct": (0, 100),
    "confirmBars": (1, 100),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "maxTradesPerDay": (1, 50),
    "cooldownBars": (0, 200),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "rrRatio": (0.2, 10.0),
    "minRR": (0.0, 20.0),
    "fibMinPct": (0.0, 100.0),
    "fibMaxPct": (0.0, 150.0),
    "tpExtensionPct": (-100.0, 500.0),
    "maxHoldBars": (0, 5000),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class JssConfig(StrategyConfig, EntryOrderFields, EntryFilterFields):
    """BOS / CHoCH na TF štruktúry → SD zóna, ktorá ho spôsobila → vstup pri návrate do nej."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- 🧭 Štruktúra ---------------------------------------------------- #
    structTF: int = 240
    #: TF zóny na upresnenie vstupu v zóne TF štruktúry (0 = vypnuté; musí byť nižší než structTF)
    refineTF: int = 15
    swingLen: int = 3
    triggerMode: TriggerMode = TriggerMode.BOTH
    atrLen: int = 14
    # ---- 🟦 SD zóna ------------------------------------------------------- #
    zoneType: ZoneType = ZoneType.OB
    zoneEdge: ZoneEdge = ZoneEdge.WICK
    impulseAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.5, "atr"))
    baseMaxBars: int = 3
    zoneMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    zoneMaxAtr: SizeSpec = field(default_factory=lambda: SizeSpec(3.0, "atr"))
    zoneMaxAgeBars: int = 100
    # ---- 🔢 Fibonacci (noha BOS) ------------------------------------------- #
    #: Fibonacci cez nohu, ktorá BOS spravila: 100 % = jej začiatok, 0 % = jej koniec (extrém po BOS, kým sa
    #: cena nevráti do zóny). Zóna sa obchoduje, len keď vstup leží medzi `fibMinPct` a `fibMaxPct` návratu
    #: (30. 9. / 2. 10. 2026: Fibo zakomponované do JSS). Vypnuté = správanie ako doteraz.
    useFibo: bool = False
    fibMinPct: float = 50.0
    fibMaxPct: float = 100.0
    # ---- 🎯 Vstup --------------------------------------------------------- #
    entryModel: EntryModel = EntryModel.TOUCH
    entryDepthPct: int = 0
    confirmBars: int = 6
    imbMinSizeAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    pbWickPct: int = 60
    pbBodyPct: int = 30
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 5
    cooldownBars: int = 0
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slFrom: SlFrom = SlFrom.REFINED
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    #: rezerva stopu v bodoch ceny za zónou — priestor na výber likvidity (pripočíta sa k ATR rezerve)
    slBufferPoints: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 2.0
    minRR: float = 1.0
    #: Cieľ pri `tpMode=extension`: extenzia za koniec nohy v % jej dĺžky (27 = −27 %, 61.8 = −61,8 %, 0 = koniec nohy).
    tpExtensionPct: float = 27.0
    maxHoldBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showStructure: bool = True
    showZones: bool = True
    showFibo: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    legacyPineSizing: bool = False
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

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
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.pbBodyPct + self.pbWickPct > 100:
            yield f"pbWickPct + pbBodyPct = {self.pbWickPct + self.pbBodyPct} > 100 — pin bar nemôže vzniknúť"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
        if self.useFibo and self.fibMinPct >= self.fibMaxPct:
            yield "Fibonacci: fibMinPct musí byť menej než fibMaxPct"
        if self.zoneMaxAtr.value and self.zoneMinAtr.value > self.zoneMaxAtr.value:
            yield "zoneMinAtr musí byť najviac zoneMaxAtr"
