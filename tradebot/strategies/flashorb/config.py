"""Config FLASH TRIGGER ORB 1.0 — high / low jednej vybranej sviečky, prieraz zavretím (port `FlashTriggerOrb`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 7). Čas sviečky = UTC + `utcOffset` (pevný posun, bez letného času).
  * **range** — sviečka s časom `targetHour`:`targetMinute` (deň podľa filtra dní) dá high / low,
  * **vstup** — od ďalšieho baru zavretie nad high long / pod low short, jeden obchod na range (deň),
  * **stop / cieľ** — druhá strana sviečky, cieľ `riskReward` × stop; voliteľný trailing (body),
  * **koniec dňa** — raz za deň UTC od `eodHour`:`eodMinute` zavrieť pozíciu (nové vstupy neblokuje)."""

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

__all__ = ["FlashorbConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'targetHour': (0, 23),
    'targetMinute': (0, 59),
    'utcOffset': (-12, 14),
    'riskReward': (0.1, 20.0),
    'trailActivatePoints': (0.1, 10000.0),
    'trailBufferPoints': (0.1, 10000.0),
    'eodHour': (0, 23),
    'eodMinute': (0, 59),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class FlashorbConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config FLASH TRIGGER ORB 1.0 — high / low jednej vybranej sviečky, prieraz zavretím (port `FlashTriggerOrb`)."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕯️ Vybraná sviečka ---------------------------------------------------- #
    targetHour: int = 14
    targetMinute: int = 30
    utcOffset: int = 0
    dayFilter: bool = False
    tradeMonday: bool = True
    tradeTuesday: bool = True
    tradeWednesday: bool = True
    tradeThursday: bool = True
    tradeFriday: bool = True
    # ---- 🛡️ Stop, cieľ a koniec dňa -------------------------------------------- #
    riskReward: float = 3.0
    activateTrailing: bool = False
    trailActivatePoints: float = 50.0
    trailBufferPoints: float = 20.0
    useEodClose: bool = True
    eodHour: int = 23
    eodMinute: int = 59
    riskDollar: float = 100.0
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
