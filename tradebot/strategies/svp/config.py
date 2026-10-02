"""Config stratégie Volume Profile POC — seansový volume profile (SVP) a obchod na jeho POC.

Zadanie používateľa (2. 10. 2026): klasický SVP na báze New York seansy a klasické vstupy na POC —
keď je cena pod POC, na dotyk POC short (POC je odpor), keď je nad ním, na dotyk long (podpora);
vstup na dotyk limitkou alebo cez vstupné modely (IBS imbalance, pin bar). K tomu prerazenie POC
a jeho retest: cena POC prerazí zavretím a pri návrate k nemu sa vstupuje v smere prerazenia.

Profil sa počíta z barov grafu: objem každého baru sa rovnomerne rozloží do cenových riadkov
medzi jeho low a high (`rowTicks` tickov na riadok). POC je riadok s najväčším objemom, value
area (VAH – VAL) je `valueAreaPct` % objemu okolo neho. Úroveň na obchodovanie je POC
**predošlej** seansy (hotový profil, pevná úroveň na celý deň) alebo **vyvíjajúci sa** POC
dnešnej seansy. Stratégia nemá Pine predlohu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["SvpConfig", "PocSource", "TradeMode", "EntryModel", "SlMode", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class PocSource(str, Enum):
    PREVIOUS = "previous"      # POC predošlej (uzavretej) seansy — pevná úroveň na celý deň
    DEVELOPING = "developing"  # vyvíjajúci sa POC dnešnej seansy — hýbe sa s objemom


class TradeMode(str, Enum):
    REJECTION = "rejection"  # dotyk POC z tej strany, kde cena je (pod POC short, nad POC long), bez čerstvého prerazenia
    RETEST = "retest"        # len po prerazení POC zavretím: návrat k POC a vstup v smere prerazenia
    BOTH = "both"


class EntryModel(str, Enum):
    TOUCH = "touch"          # limitka na POC
    IMBALANCE = "imbalance"  # po dotyku IBS imbalance v smere
    PINBAR = "pinbar"        # po dotyku pin bar v smere
    ANY = "any"              # imbalance alebo pin bar


class SlMode(str, Enum):
    ATR = "atr"        # násobok ATR od vstupu
    POINTS = "points"  # pevné body ceny od vstupu


class TpMode(str, Enum):
    RR = "rr"            # násobok stopu
    VA_EDGE = "va_edge"  # hrana value area v smere obchodu (long VAH, short VAL)


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "awayAtr": "atr",
    "touchTolAtr": "atr",
    "breakBufferAtr": "atr",
    "imbMinSizeAtr": "atr",
    "slAtr": "atr",
    "slPoints": "abs",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "pocSource": PocSource,
    "tradeMode": TradeMode,
    "entryModel": EntryModel,
    "slMode": SlMode,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sessionStartH": (0, 23),
    "sessionStartM": (0, 59),
    "sessionEndH": (0, 23),
    "sessionEndM": (0, 59),
    "rowTicks": (1, 10000),
    "valueAreaPct": (10, 99),
    "retestMaxBars": (1, 2000),
    "confirmBars": (1, 100),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "maxTradesPerDay": (1, 50),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "rrRatio": (0.2, 20.0),
    "minRR": (0.0, 20.0),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class SvpConfig(StrategyConfig, EntryOrderFields):
    """Seansový volume profile; obchod na dotyk POC (odmietnutie) a na retest po jeho prerazení."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES

    # ---- 📊 Volume profile (seansa) --------------------------------------- #
    #: Seansa profilu v pásme America/New_York (9:30–16:00 = cash seansa).
    sessionStartH: int = 9
    sessionStartM: int = 30
    sessionEndH: int = 16
    sessionEndM: int = 0
    #: Výška riadku profilu v tickoch (MNQ: 4 ticky = 1 bod).
    rowTicks: int = 4
    valueAreaPct: int = 70
    pocSource: PocSource = PocSource.PREVIOUS
    # ---- 🎯 Vstup ---------------------------------------------------------- #
    tradeMode: TradeMode = TradeMode.BOTH
    entryModel: EntryModel = EntryModel.TOUCH
    #: Cena musí najprv zavrieť aspoň toľko ATR od POC — až potom je návrat k nemu „dotyk".
    awayAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    #: Dotyk: cena príde k POC bližšie než toľko ATR (pre vstupné modely; limitka je presne na POC).
    touchTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    #: Prerazenie: zavretie za POC aspoň o toľko ATR.
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.25, "atr"))
    #: Retest najneskôr toľko barov po prerazení.
    retestMaxBars: int = 48
    #: Po dotyku sa na vstupný model čaká najviac toľko barov.
    confirmBars: int = 4
    imbMinSizeAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.05, "atr"))
    pbWickPct: int = 60
    pbBodyPct: int = 30
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 2
    # ---- 🚦 Okno obchodovania --------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = True
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 15
    tradeEndM: int = 30
    #: Zavrieť pozíciu na konci okna obchodovania.
    closeAtWindowEnd: bool = False
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slMode: SlMode = SlMode.ATR
    slAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    slPoints: SizeSpec = field(default_factory=lambda: SizeSpec(20.0, "abs"))
    atrLen: int = 14
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 1.5
    minRR: float = 1.0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showPoc: bool = True
    showValueArea: bool = True
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
    def session_start(self) -> int:
        return self.sessionStartH * 60 + self.sessionStartM

    @property
    def session_end(self) -> int:
        return self.sessionEndH * 60 + self.sessionEndM

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
        if self.session_end <= self.session_start:
            yield "seansa profilu: koniec musí byť za začiatkom (seansa cez polnoc sa nepodporuje)"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.pbBodyPct + self.pbWickPct > 100:
            yield f"pbWickPct + pbBodyPct = {self.pbWickPct + self.pbBodyPct} > 100 — pin bar nemôže vzniknúť"
