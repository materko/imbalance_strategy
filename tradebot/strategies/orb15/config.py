"""Config ORB 15/5 1.0 — 15m opening range, vstup na zavretí 5m sviečky (port Rust `Orb15m5mBreakout`, `rq_sdk`).

Zadanie týždňa 31. 10. 2026 (roboquant šablóna 6). Pravidlá a defaulty z predlohy; vedomé zmeny:
`allowLong` / `allowShort` sú predvolene zapnuté (predloha ich má vypnuté = bez obchodov), veľkosť z `riskDollar`.

  * **OR** — high / low barov s otvorením `orStart` ≤ t < `orStart` + `orMinutes` (New York),
  * **bias dňa** — prvý bar po `biasCheck` (najskôr po OR): zavretie pod low predošlého dňa → bez longov,
    nad high → bez shortov (deň = obchodný deň CME od 18:00 NY),
  * **vstup** — zavretie nad OR high long / pod OR low short, market; filter knôtu proti smeru (% sviečky),
    najviac `maxTradesPerDay` obchodov, nie po `lastEntry`,
  * **stop / cieľ** — druhá strana OR, cieľ `rr` × stop alebo `targetPoints` bodov,
  * **koniec** — `closeAtEnd`: od `lastEntry` pozíciu zavrieť.
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

__all__ = ["Orb15Config", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "orStart": (0, 2359), "orMinutes": (5, 120), "lastEntry": (0, 2359), "targetMode": (0, 1), "rr": (0.25, 20.0),
    "targetPoints": (0.1, 5000.0), "maxTradesPerDay": (1, 5), "maxWickPct": (0.0, 99.9), "biasCheck": (0, 2359),
    "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class Orb15Config(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """OR 9:30–9:45 NY, prieraz zavretím, stop na druhej strane OR, cieľ RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕘 Opening range (New York, HHMM) ---------------------------------- #
    orStart: int = 930
    orMinutes: int = 15
    lastEntry: int = 1600
    # ---- 🎯 Vstup ------------------------------------------------------------- #
    allowLong: bool = True
    allowShort: bool = True
    maxTradesPerDay: int = 1
    useWickFilter: bool = False
    maxWickPct: float = 50.0
    useDailyBias: bool = True
    biasCheck: int = 915
    # ---- 🛡️ Cieľ a koniec --------------------------------------------------- #
    #: 0 = RR, 1 = pevné body
    targetMode: int = 0
    rr: float = 2.0
    targetPoints: float = 40.0
    closeAtEnd: bool = True
    # ---- 💰 Veľkosť ------------------------------------------------------------- #
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia --------------------------------------------------------- #
    drawRange: bool = True
    # ---- rozšírenia portu --------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        for name in ("orStart", "lastEntry", "biasCheck"):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
