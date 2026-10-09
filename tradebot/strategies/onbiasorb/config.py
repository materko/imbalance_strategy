"""Config stratégie Overnight Bias ORB — smer dňa z polohy ceny v overnight range, prerazenie 15m opening rangu.

Doslovný port Pine v6 skriptu „Overnight Bias ORB (NQ 15m)" (video „Hedge Fund Manager TOP 3 Strategies",
Matteo Conti / IQ Capital), `docs/sources/overnight_bias_orb.pine`. Časy sú v HHMM pásma America/Chicago.
Priemerný ATR je ten istý výpočet ako vo Volt Break (`tradebot.strategies.voltbreak.avgatr`).
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

from ..voltbreak.config import AtrSource, hhmm_minutes

__all__ = ["OnBiasOrbConfig", "AtrSource", "CONFIG_DIR", "hhmm_minutes"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "onStartHHMM": (0, 2359),
    "rthHHMM": (0, 2359),
    "exitHHMM": (0, 2359),
    "minEntryHHMM": (0, 2359),
    "atrLen": (1, 100),
    "avgLen": (1, 100),
    "slPct": (1.0, 500.0),
    "rr": (0.1, 20.0),
    "adxLen": (2, 100),
    "adxMin": (0.0, 100.0),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"useTimeExit", "riskDollar", "legacyPineSizing", "leverage", "showLevels"})


@dataclass
class OnBiasOrbConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Parametre Overnight Bias ORB. Defaulty = Pine skript."""

    ENUM_FIELDS: ClassVar[dict[str, type]] = {"atrSource": AtrSource, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕐 Čas (CT) --------------------------------------------------------- #
    onStartHHMM: int = 0
    rthHHMM: int = 830
    exitHHMM: int = 1430
    #: časový výstup (ako vo videu); vypnutý = drží do SL / TP
    useTimeExit: bool = True
    minEntryHHMM: int = 900
    # ---- 🛡️ SL / TP ---------------------------------------------------------- #
    atrLen: int = 14
    avgLen: int = 15
    slPct: float = 30.0
    rr: float = 3.0
    atrSource: AtrSource = AtrSource.SESSION
    # ---- 📈 ADX --------------------------------------------------------------- #
    adxLen: int = 14
    adxMin: float = 20.0
    # ---- 🧩 Rozšírenia portu ------------------------------------------------- #
    #: Pine má 1 kontrakt — veľkosť z rizika je rozšírenie portu.
    riskDollar: float = 300.0
    legacyPineSizing: bool = False
    leverage: float = 1.0
    showLevels: bool = True

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return 1.0
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        for name in ("onStartHHMM", "rthHHMM", "exitHHMM", "minEntryHHMM"):
            if int(getattr(self, name)) % 100 > 59:
                yield f"{name}={getattr(self, name)} nie je platný čas HHMM"
        if hhmm_minutes(self.exitHHMM) <= hhmm_minutes(self.rthHHMM):
            yield f"časový exit {self.exitHHMM} musí byť po opene {self.rthHHMM}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
