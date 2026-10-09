"""Config stratégie Volt Break — prerazenie „noise" hranice nad open o polnoci, len long, 30m graf.

Doslovný port Pine v6 skriptu „Volt Break (NQ 30m)" (video „Hedge Fund Manager TOP 3 Strategies",
Matteo Conti / IQ Capital), `docs/sources/volt_break.pine`. Časy sú v HHMM pásma America/Chicago.
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

__all__ = ["VoltBreakConfig", "AtrSource", "CONFIG_DIR", "hhmm_minutes"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class AtrSource(str, Enum):
    """Pine „Zdroj ATR"."""

    SESSION = "Seansa 0:00–16:00 CT (ako vo videu)"
    DAILY = "Denné sviečky burzy"


def hhmm_minutes(hhmm: int) -> int:
    """Pine `toMin`: 1430 -> 870 minút od polnoci."""
    return int(hhmm) // 100 * 60 + int(hhmm) % 100


CONSTRAINTS: dict[str, tuple[float, float]] = {
    "noisePct": (0.0, 500.0),
    "atrLen": (1, 100),
    "avgLen": (1, 100),
    "tpUsd": (0.0, 100000.0),
    "slUsd": (1.0, 100000.0),
    "maxTrades": (1, 20),
    "startHHMM": (0, 2359),
    "endHHMM": (0, 2359),
    "usdPerPoint": (0.01, 1000.0),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"useTimeExit", "usdPerPoint", "riskDollar", "legacyPineSizing", "leverage", "showLevels"})


@dataclass
class VoltBreakConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Parametre Volt Break. Defaulty = Pine skript."""

    ENUM_FIELDS: ClassVar[dict[str, type]] = {"atrSource": AtrSource, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🔊 Noise hranica ---------------------------------------------------- #
    noisePct: float = 30.0
    atrLen: int = 14
    avgLen: int = 15
    atrSource: AtrSource = AtrSource.SESSION
    # ---- 🎯 TP / SL a obchody ------------------------------------------------ #
    tpUsd: float = 800.0
    slUsd: float = 1500.0
    maxTrades: int = 3
    # ---- 🕐 Čas (CT) --------------------------------------------------------- #
    startHHMM: int = 1000
    endHHMM: int = 1430
    #: časový výstup (ako vo videu); vypnutý = drží do SL / TP
    useTimeExit: bool = True
    # ---- 🧩 Rozšírenia portu ------------------------------------------------- #
    #: Koľko $ je pohyb o 1 bod na kontrakte, pre ktorý sú `tpUsd`/`slUsd` písané. Pine ich prepočíta cez
    #: `syminfo.pointvalue` grafu; skript je písaný na NQ (20 $/bod) — tak sa TP 800 $ = 40 bodov aj na MNQ.
    usdPerPoint: float = 20.0
    #: Pine má 1 kontrakt — veľkosť z rizika je rozšírenie portu.
    riskDollar: float = 150.0
    legacyPineSizing: bool = False
    leverage: float = 1.0
    showLevels: bool = True

    @property
    def tp_points(self) -> float:
        return self.tpUsd / self.usdPerPoint

    @property
    def sl_points(self) -> float:
        return self.slUsd / self.usdPerPoint

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return 1.0
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        for name in ("startHHMM", "endHHMM"):
            if int(getattr(self, name)) % 100 > 59:
                yield f"{name}={getattr(self, name)} nie je platný čas HHMM"
        if hhmm_minutes(self.endHHMM) <= hhmm_minutes(self.startHHMM):
            yield f"koniec vstupov {self.endHHMM} musí byť po začiatku {self.startHHMM}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
