"""Config stratégie NOC + PONDELOK 1.0 — nočný drift Nasdaqu a silný pondelok, len v rastovom trende.

Z merania na MNQ 5/2019 – 9/2026 (prieskum 18. 10. 2026, iCloud NASDAQ-STUDIUM):

  * **noc**: long o 15:55 NY, výstup o 3:00 NY ďalší obchodný deň (piatok → pondelok 3:00) — zisk Nasdaqu
    vzniká hlavne mimo seansy, úsek 3:00–9:30 (Londýn) už nepridáva,
  * **pondelok**: long 9:30 → 15:55 NY (jediný deň s jasne kladným priemerom RTH),
  * **trend**: obe len keď je denné zavretie (15:55 NY) nad SMA `smaLen` denných zavretí; pondelok berie piatkové,
  * noci v týždni rollu kontraktu (marec, jún, september, december, dni `rollFromDay`–`rollToDay`) sa vynechajú —
    v spojitých dátach bez back-adjustmentu je v tú noc skok medzi kontraktmi, nie pohyb trhu.

Bez cieľa a bez stopu (výstup v čase); `stopPct` je voliteľná poistka v % ceny.
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

__all__ = ["NocPonConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "nightEntryH": (0, 23), "nightEntryM": (0, 59), "nightExitH": (0, 23), "nightExitM": (0, 59),
    "monEntryH": (0, 23), "monEntryM": (0, 59), "monExitH": (0, 23), "monExitM": (0, 59),
    "closeRefH": (0, 23), "closeRefM": (0, 59), "smaLen": (2, 400),
    "rollFromDay": (1, 31), "rollToDay": (1, 31), "stopPct": (0.0, 20.0),
    "qty": (0.001, 1000), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class NocPonConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Long cez noc (15:55 → 3:00 NY) a v pondelok cez deň (9:30 → 15:55), len nad SMA denných zavretí."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🌙 Noc (čas New York) ---------------------------------------------- #
    useNight: bool = True
    nightEntryH: int = 15
    nightEntryM: int = 55
    #: Výstup v nasledujúci obchodný deň (piatok → pondelok); keď je čas po vstupe, v ten istý večer.
    nightExitH: int = 3
    nightExitM: int = 0
    # ---- 📅 Pondelok -------------------------------------------------------- #
    useMonday: bool = True
    monEntryH: int = 9
    monEntryM: int = 30
    monExitH: int = 15
    monExitM: int = 55
    # ---- 📈 Trend ----------------------------------------------------------- #
    #: Obchodovať len keď je denné zavretie nad SMA `smaLen` denných zavretí (pondelok: piatkové).
    useTrend: bool = True
    smaLen: int = 100
    #: Čas „denného zavretia“ pre SMA (New York).
    closeRefH: int = 15
    closeRefM: int = 55
    # ---- 🔁 Roll kontraktu --------------------------------------------------- #
    #: Vynechať noci v dňoch `rollFromDay`–`rollToDay` mesiacov marec / jún / september / december.
    skipRoll: bool = True
    rollFromDay: int = 7
    rollToDay: int = 16
    # ---- 🛡️ Poistka ----------------------------------------------------------- #
    #: Stop v % ceny od vstupu (0 = bez stopu, výstup len v čase).
    stopPct: float = 0.0
    # ---- 💰 Veľkosť ----------------------------------------------------------- #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------ #
    showSma: bool = True
    # ---- rozšírenia portu ---------------------------------------------------- #
    leverage: float = 1.0

    @staticmethod
    def _m(h: int, m: int) -> int:
        return h * 60 + m

    @property
    def night_entry(self) -> int:
        return self._m(self.nightEntryH, self.nightEntryM)

    @property
    def night_exit(self) -> int:
        return self._m(self.nightExitH, self.nightExitM)

    @property
    def mon_entry(self) -> int:
        return self._m(self.monEntryH, self.monEntryM)

    @property
    def mon_exit(self) -> int:
        return self._m(self.monExitH, self.monExitM)

    @property
    def close_ref(self) -> int:
        return self._m(self.closeRefH, self.closeRefM)

    def _problems(self) -> Iterable[str]:
        if not (self.useNight or self.useMonday):
            yield "zapni aspoň jeden obchod (useNight alebo useMonday)"
        if self.mon_exit <= self.mon_entry:
            yield "pondelok: výstup musí byť po vstupe"
        if self.night_exit == self.night_entry:
            yield "noc: výstup nesmie byť v čase vstupu"
        if self.rollToDay < self.rollFromDay:
            yield "roll: rollToDay musí byť aspoň rollFromDay"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
