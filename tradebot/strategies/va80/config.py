"""Config MTK RANGE 1.0 — pravidlo 80 % (Market Profile): otvorenie mimo včerajšej value area a návrat do nej.

Prieskum 7. 11. 2026 (MNQ 2021–2026, `.nightsearch/range`): na Nasdaqu stabilný edge v 5 z 5 rokov, iný zdroj dát
(NAS100) potvrdil; na ES a MGC nie. Časy New York, RTH 9:30–16:00.
  * **value area** — z barov RTH predošlého dňa (zavretie a objem), koše `vaBinPct` % ceny, `vaPct` % objemu
    (`vaMethod` rank = najväčšie koše, expand = rozširovanie od POC),
  * **podmienka dňa** — otvorenie RTH nad VAH (pod VAL) aspoň o `minOpenOutside` šírky VA,
  * **vstup** — prvé zavretie sviečky `returnBarMin` minút (od 9:30) späť vo VA, najneskôr do `lastEntry`: short
    (long) market, jeden obchod za deň,
  * **stop** za extrémom dňa od otvorenia + `slBufferVa` × šírka VA (obchod sa preskočí, keď je stop ďalej ako
    `maxStopAtr` × denné ATR 14 dní RTH; 0 = bez filtra), **cieľ** POC / opačný okraj VA / stred VA,
  * **výstup v čase** o `exitTime` (podstata intraday stratégie)."""

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

__all__ = ["Va80Config", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    'vaPct': (50.0, 95.0),
    'vaBinPct': (0.01, 0.5),
    'returnBarMin': (5, 60),
    'minOpenOutside': (0.0, 2.0),
    'lastEntry': (930, 1559),
    'exitTime': (1000, 1600),
    'slBufferVa': (0.0, 1.0),
    'minRR': (0.0, 5.0),
    'maxStopAtr': (0.0, 5.0),
    'riskDollar': (0, 100000),
    'leverage': (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage", "riskDollar"})


@dataclass
class Va80Config(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Config MTK RANGE 1.0 — pravidlo 80 % (Market Profile): otvorenie mimo včerajšej value area a návrat do nej."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📊 Value area (predošlý deň RTH) --------------------------------------- #
    vaPct: float = 70.0
    vaBinPct: float = 0.03
    vaMethod: str = 'expand'
    # ---- 🕘 Návrat a vstup (New York) ------------------------------------------- #
    returnBarMin: int = 30
    minOpenOutside: float = 0.0
    lastEntry: int = 1200
    exitTime: int = 1555
    allowLong: bool = True
    allowShort: bool = True
    # ---- 🛡️ Stop a cieľ -------------------------------------------------------- #
    tpMode: str = 'opp'
    slBufferVa: float = 0.0
    minRR: float = 0.5
    maxStopAtr: float = 0.0
    fixedQty: bool = True
    riskDollar: float = 500.0
    showLevels: bool = True
    # ---- rozšírenia portu ------------------------------------------------------- #
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        for name in ("lastEntry", "exitTime"):
            v = int(getattr(self, name))
            if v % 100 > 59:
                yield f"{name}={v}: minúty musia byť 00–59 (HHMM)"
        if self.vaMethod not in ("rank", "expand"):
            yield f"vaMethod={self.vaMethod!r}: rank alebo expand"
        if self.tpMode not in ("poc", "opp", "mid"):
            yield f"tpMode={self.tpMode!r}: poc, opp alebo mid"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
