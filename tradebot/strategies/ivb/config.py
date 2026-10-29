"""Config stratégie IVB 1.0 — Initial Volatility Breakout (port Rust stratégie pre `rq_sdk`, zadanie používateľa 29. 10. 2026).

Prepis „len pre porovnanie“: pravidlá, defaulty aj správanie predlohy 1 : 1, vrátane jej zvláštností
(v `engine.py` popísané pri mieste, kde nastávajú). Jediná vedomá zmena: veľkosť z rizika v $ (`riskDollar`,
konvencia repozitára) namiesto `risk_pct` % účtu — engine stav účtu nepozná.

  * **IB** — high / low barov s časom (New York, HHMM) `sessionStart` ≤ t < `sessionEnd` (9:30–10:00),
  * **vstup** — `sessionEnd` ≤ t < `entryWindowEnd`, bez pozície, menej ako `maxTradesPerDay` pokusov:
    IB / priemer posledných `ibRangeLookback` IB v [`minContractionRatio`, `maxContractionRatio`] a objem baru
    ≥ `volSurgeMult` × priemer posledných `volAvgBars` objemov RTH (9:30–16:00, vrátane tohto baru)
    → zavretie nad IB high = long, pod IB low = short, market,
  * **stop / cieľ** — `slAtrMult` / `tpAtrMult` × ATR (`atrPeriod`, Wilder) od zavretia signálneho baru,
  * **koniec dňa** — `flattenEod`: o `eodFlatten` (a pri zmene dňa) zavrieť pozíciu.
"""

from __future__ import annotations

from dataclasses import dataclass
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

__all__ = ["IvbConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "sessionStart": (0, 2359), "sessionEnd": (0, 2359), "entryWindowEnd": (1000, 1600), "direction": (0, 2),
    "maxContractionRatio": (0.05, 2.0), "minContractionRatio": (0.0, 1.0), "ibRangeLookback": (5, 200),
    "volSurgeMult": (0.5, 10.0), "volAvgBars": (5, 100), "atrPeriod": (2, 100),
    "slAtrMult": (0.5, 5.0), "tpAtrMult": (0.5, 10.0), "eodFlatten": (0, 2359), "maxTradesPerDay": (1, 10),
    "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class IvbConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """IB 9:30–10:00 NY, prieraz zavretím v okne do 16:00 pri stlačenom IB a náraste objemu, stop / cieľ v ATR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕘 Seansa (New York, HHMM) ------------------------------------------- #
    sessionStart: int = 930
    sessionEnd: int = 1000
    entryWindowEnd: int = 1600
    # ---- 🎯 Smer --------------------------------------------------------------- #
    #: 0 = oba, 1 = len long, 2 = len short
    direction: int = 0
    # ---- 📏 Stlačený IB (voči priemeru posledných IB) -------------------------- #
    maxContractionRatio: float = 0.9
    minContractionRatio: float = 0.0
    ibRangeLookback: int = 10
    # ---- 📊 Objem --------------------------------------------------------------- #
    volSurgeMult: float = 1.1
    volAvgBars: int = 5
    # ---- 🛡️ Stop a cieľ --------------------------------------------------------- #
    atrPeriod: int = 14
    slAtrMult: float = 3.0
    tpAtrMult: float = 2.0
    flattenEod: bool = False
    eodFlatten: int = 1600
    maxTradesPerDay: int = 2
    # ---- 💰 Veľkosť ------------------------------------------------------------- #
    #: Riziko na obchod v $ (predloha: `risk_pct` = 2 % účtu).
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia --------------------------------------------------------- #
    drawIbZone: bool = True
    # ---- rozšírenia portu --------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        for name in ("sessionStart", "sessionEnd", "entryWindowEnd", "eodFlatten"):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if self.sessionEnd <= self.sessionStart:
            yield "IB: koniec musí byť za začiatkom"
        if self.minContractionRatio > self.maxContractionRatio:
            yield "pomer IB: minimum je väčšie ako maximum"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
