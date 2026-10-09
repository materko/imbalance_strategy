"""Config stratégie VWAP ADX — pullback k VWAP po prerazení opening rangu, s filtrom ADX.

Doslovný port Pine v6 skriptu „VWAP ADX Pullback (NQ 1m)" (video „Hedge Fund Manager TOP 3
Strategies", Matteo Conti / IQ Capital), `docs/sources/vwap_adx.pine`. Len long, 1m graf NQ/MNQ.
Časy sú v HHMM pásma America/Chicago, ako v Pine (8:30 CT = 9:30 New York).
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

__all__ = ["VwapAdxConfig", "VwapAnchor", "CONFIG_DIR", "hhmm_minutes"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class VwapAnchor(str, Enum):
    """Odkiaľ sa VWAP počíta (Pine `ta.vwap(hlc3, anchor)`)."""

    RTH = "RTH 8:30 CT"      # od začiatku opening rangu
    MIDNIGHT = "Polnoc CT"   # od polnoci Chicaga


def hhmm_minutes(hhmm: int) -> int:
    """Pine `toMin`: 830 -> 510 minút od polnoci."""
    return int(hhmm) // 100 * 60 + int(hhmm) % 100


ENUM_FIELDS: dict[str, type] = {"vwapAnchor": VwapAnchor}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "orStartHHMM": (0, 2359),
    "orEndHHMM": (0, 2359),
    "exitHHMM": (0, 2359),
    "adxLen": (2, 100),
    "adxMin": (0.0, 100.0),
    "tpBars": (1, 200),
    "slBars": (1, 200),
    "maxTrades": (1, 20),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"useTimeExit", "riskDollar", "legacyPineSizing", "leverage", "showVwap", "showRange"})


@dataclass
class VwapAdxConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Parametre VWAP ADX. Defaulty = Pine skript."""

    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕐 Opening range a čas ------------------------------------------ #
    orStartHHMM: int = 830
    orEndHHMM: int = 900
    exitHHMM: int = 1555
    #: časový výstup (ako vo videu); vypnutý = drží do SL / TP
    useTimeExit: bool = True
    # ---- 📈 VWAP a ADX ----------------------------------------------------- #
    vwapAnchor: VwapAnchor = VwapAnchor.RTH
    adxLen: int = 14
    adxMin: float = 20.0
    # ---- 🎯 TP / SL a obchody ---------------------------------------------- #
    tpBars: int = 5
    slBars: int = 20
    maxTrades: int = 1
    # ---- 🧩 Rozšírenia portu ----------------------------------------------- #
    #: Pine má natvrdo 1 kontrakt — riziko na obchod je rozšírenie portu.
    riskDollar: float = 100.0
    #: Doslovný Pine sizing: vždy 1 kontrakt bez ohľadu na riziko.
    legacyPineSizing: bool = False
    leverage: float = 1.0
    showVwap: bool = True
    showRange: bool = True

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return 1.0
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        for name in ("orStartHHMM", "orEndHHMM", "exitHHMM"):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v} nie je platný čas HHMM"
        s, e, x = (hhmm_minutes(self.orStartHHMM), hhmm_minutes(self.orEndHHMM), hhmm_minutes(self.exitHHMM))
        if e <= s:
            yield f"koniec opening rangu {self.orEndHHMM} musí byť po jeho začiatku {self.orStartHHMM}"
        if x <= e:
            yield f"časový exit {self.exitHHMM} musí byť po konci opening rangu {self.orEndHHMM}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
