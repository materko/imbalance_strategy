"""Config stratégie SPX sila 1.0 (kľúč `mag7`, pôvodne „Mag7 + SPX sila") — sila pohybu S&P 500 (voliteľne + Mag7) od otvorenia NY.

Port Pine stratégie „Mag7 + SPX sila od NY open" (TradingView, október 2026, mimo repozitára):

  * od 9:30 NY sa pre každú akciu Mag7 (AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA) a index S&P 500
    počíta pohyb od otváracej ceny 9:30 v % na 1m dátach,
  * **sila** −10 až +10 = veľkosť pohybu (v násobkoch bežného pohybu po `waitMin` minútach, priemer
    `typDays` dní) a zhoda smeru symbolov, vážené `wMag` / `wBreadth`,
  * vstup v okne `waitMin`–`entryEnd` minút po otvorení (na zavretí sviečky grafu, market), raz za deň:
    long pri sile ≥ `thr` a cene Nasdaqu (symbol grafu) nad VWAP od 9:30, nad EMA a nad čiarou MAG7,
    short zrkadlovo,
  * stop v bodoch alebo za open NY (+ rezerva), cieľ `rr` × skutočný stop, voliteľne zatvorenie v čase.

Predvolené hodnoty sú nastavenia, s ktorými používateľ stratégiu púšťa na 15m grafe (6. 10. 2026);
kde sa líšia od Pine defaultu, je to pri poli poznamenané.

Dáta symbolov sily nie sú na grafe — číta ich feeder stratégie (`data.py`) z 1m skladu sviečok
(`data/tester/<zdroj>/<trh>/<SYMBOL>-1m.feather`); symbol je kľúč nástroja z `INSTRUMENTS`.
S&P 500 je Dukascopy US500 (CFD na index, ten istý pohyb ako SPX).
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
from tradebot.core.types import INSTRUMENTS, SizeUnit

__all__ = ["Mag7Config", "SlMode", "CONFIG_DIR", "SYMBOL_FIELDS"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: Polia so symbolmi sily v poradí Pine (s1 … s8); s8 je index s váhou `spxW`.
SYMBOL_FIELDS: tuple[str, ...] = ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8")


class SlMode(str, Enum):
    POINTS = "points"  # Pine „Body": stop v bodoch od vstupu
    OPEN = "open"      # Pine „Za open NY": za otváraciu cenu NY (+ rezerva); na zlej strane vstupu body


SIZE_FIELDS: dict[str, SizeUnit] = {}

ENUM_FIELDS: dict[str, type] = {"slMode": SlMode}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "thr": (0.5, 10.0),
    "waitMin": (1, 390),
    "entryEnd": (1, 390),
    "openH": (0, 23),
    "openM": (0, 59),
    "sessEndH": (0, 23),
    "sessEndM": (0, 59),
    "qty": (0.001, 1000),
    "emaLen": (1, 1000),
    "magLen": (1, 500),
    "minMove": (0.0, 10000.0),
    "slPts": (0.1, 10000.0),
    "slOpenBuf": (0.0, 10000.0),
    "rr": (0.1, 50.0),
    "eodH": (0, 23),
    "eodM": (0, 59),
    "typDays": (3, 250),
    "zFull": (0.1, 20.0),
    "wMag": (0.0, 100.0),
    "wBreadth": (0.0, 100.0),
    "spxW": (0.0, 100.0),
    "stockW": (0.0, 100.0),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"spxOnly", "stockW", "vwapData", "fixedQty", "riskDollar", "sessEndH", "sessEndM",
                                              "showLines", "leverage"})


@dataclass
class Mag7Config(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Sila S&P 500 (voliteľne + Mag7) od 9:30 NY; vstup v okne po otvorení s potvrdením VWAP / EMA / čiary sily na Nasdaqu."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES

    # ---- ⏱️ Vstup ---------------------------------------------------------- #
    thr: float = 5.0
    waitMin: int = 10           # Pine default 15
    entryEnd: int = 30
    openH: int = 9
    openM: int = 30
    allowL: bool = True
    allowS: bool = True
    # ---- ✅ Potvrdenie na Nasdaqu (symbol grafu) ----------------------------- #
    useVwap: bool = True
    useEma: bool = True
    emaLen: int = 50            # Pine default 100
    useMag: bool = True         # Pine default vypnuté
    magLen: int = 5             # Pine default 9
    useOpen: bool = False
    minMove: float = 0.0
    #: Nástroj, z ktorého 1m dát sa počíta VWAP od 9:30 (Pine: výpočtový TF 1m). Keď to nie je nástroj
    #: grafu, VWAP sa poskladá zo sviečok grafu.
    vwapData: str = "mnq_databento"
    # ---- 🚪 Výstup --------------------------------------------------------- #
    slMode: SlMode = SlMode.OPEN  # Pine default Body
    slPts: float = 20.0
    slOpenBuf: float = 2.0
    rr: float = 1.5
    useEod: bool = False        # Pine default zapnuté
    eodH: int = 15
    eodM: int = 55
    # ---- 💪 Sila pohybu ------------------------------------------------------ #
    sessEndH: int = 16
    sessEndM: int = 0
    typDays: int = 20
    zFull: float = 1.0
    wMag: float = 1.0
    wBreadth: float = 1.0
    spxW: float = 1.0
    #: Sila len z indexu (symbol 8) — tak počíta Pine Mag7 1.0 v TradingView (akcie nezachytia nový deň,
    #: 469 obchodov za 3 roky); od 7. 10. 2026 stratégia „SPX sila". Vypnuté = index + akcie s váhou `stockW`.
    spxOnly: bool = True
    #: Váha akcií Mag7 (symboly 1–7), keď `spxOnly` je vypnuté; 1 = všetkých 8 symbolov rovnako (Pine 1.1).
    stockW: float = 1.0
    # ---- 📊 Symboly (kľúče nástrojov) ----------------------------------------- #
    s1: str = "aapl_ibkr"
    s2: str = "msft_ibkr"
    s3: str = "nvda_ibkr"
    s4: str = "googl_ibkr"
    s5: str = "amzn_ibkr"
    s6: str = "meta_ibkr"
    s7: str = "tsla_ibkr"
    s8: str = "us500_dukascopy"
    # ---- 💰 Veľkosť ---------------------------------------------------------- #
    #: Pine: pevný počet kontraktov `qty`. Vypnuté = veľkosť z rizika `riskDollar`.
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------ #
    showLines: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    leverage: float = 1.0

    @property
    def open_minutes(self) -> int:
        return self.openH * 60 + self.openM

    @property
    def session_minutes(self) -> int:
        """Dĺžka NY seansy v minútach (Pine `sessStr` 0930-1600)."""
        return self.sessEndH * 60 + self.sessEndM - self.open_minutes

    @property
    def symbols(self) -> list[tuple[str, float]]:
        """(kľúč nástroja, váha) symbolov sily — Pine `ws`."""
        w = 0.0 if self.spxOnly else self.stockW
        return [(self.s1, w), (self.s2, w), (self.s3, w), (self.s4, w), (self.s5, w), (self.s6, w), (self.s7, w),
                (self.s8, self.spxW)]

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.session_minutes <= 0:
            yield "koniec seansy musí byť za otvorením NY"
        for key, _w in self.symbols:
            if key and key not in INSTRUMENTS:
                yield f"neznámy symbol sily {key!r}; známe: {sorted(INSTRUMENTS)}"
        if self.vwapData and self.vwapData not in INSTRUMENTS:
            yield f"neznámy nástroj VWAP {self.vwapData!r}"
        if self.spxW <= 0 and (self.spxOnly or self.stockW <= 0):
            yield "sila nemá z čoho počítať: spxW musí byť > 0 (pri spxOnly), inak aspoň jedna z váh stockW / spxW"
        if self.wMag + self.wBreadth <= 0:
            yield "aspoň jedna z váh wMag / wBreadth musí byť > 0"
