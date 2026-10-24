"""Config stratégie NY VA BREAKOUT 1.0 — prieraz z value area prvej newyorskej hodiny.

  * **profil**: fixed range volume profile barov od `rangeStartH:M` do `rangeEndH:M` (9:30–10:30 NY); objem baru
    sa rozloží rovnomerne do `profileRows` cenových riadkov medzi jeho low a high; POC = riadok s najväčším objemom,
    value area = `valueAreaPct` % objemu okolo POC (VAH / VAL),
  * **vstup**: po konci rangeu, do `entryEndH:M`, zavretie nad VAH → long, pod VAL → short (market na ďalšej sviečke),
  * **stop** `slBufferTicks` tickov za POC, **cieľ** `rrRatio` × riziko; voliteľne zavretie pozície o `closeH:M`.

Predvolené hodnoty sú tie isté ako v Pine skripte NY VA BREAKOUT 1.0 (iCloud VOLUME-PROFILE, nie v repozitári).
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
from tradebot.core.types import SizeUnit

__all__ = ["NyVaConfig", "CONFIG_DIR", "EntryMode", "SlCap"]


class EntryMode(str, Enum):
    CLOSE = "close"      # market po potvrdenom prieraze
    RETEST = "retest"    # po prieraze limitka na VAH / VAL


class SlCap(str, Enum):
    SKIP = "skip"        # stop nad limit → obchod sa vynechá
    CAP = "cap"          # stop sa skráti na limit

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"entryMode": EntryMode, "slCapMode": SlCap}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "rangeStartH": (0, 23), "rangeStartM": (0, 59), "rangeEndH": (0, 23), "rangeEndM": (0, 59),
    "profileRows": (10, 400), "valueAreaPct": (10.0, 95.0),
    "entryEndH": (0, 23), "entryEndM": (0, 59), "maxTradesPerDay": (1, 20),
    "confirmCloses": (1, 10), "retestBars": (1, 200), "maxSlPoints": (0, 100000), "maxSlAtr": (0, 100),
    "vaMinPoints": (0, 100000), "vaMaxPoints": (0, 100000),
    "shapePocPct": (50, 100), "shapeVaPct": (50, 100), "shapeTailPct": (0, 100),
    "rrRatio": (0.1, 10.0), "slBufferTicks": (0, 500), "closeH": (0, 23), "closeM": (0, 59),
    "qty": (0.001, 1000), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class NyVaConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Fixed range profil prvej hodiny NY; zavretie nad VAH → long, pod VAL → short, SL za POC, cieľ v RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📊 Fixed range (čas New York) ---------------------------------------- #
    rangeStartH: int = 9
    rangeStartM: int = 30
    rangeEndH: int = 10
    rangeEndM: int = 30
    #: Počet cenových riadkov profilu medzi low a high rangeu.
    profileRows: int = 60
    #: Podiel objemu okolo POC, ktorý tvorí value area.
    valueAreaPct: float = 70.0
    # ---- 🎯 Vstup -------------------------------------------------------------- #
    allowLong: bool = True
    allowShort: bool = True
    #: Posledný čas vstupu (New York); bar, ktorý sa v ňom otvára, už nevstupuje.
    entryEndH: int = 16
    entryEndM: int = 0
    maxTradesPerDay: int = 1
    #: Koľko zavretí po sebe za VAH / VAL je prieraz (1 = prvé zavretie).
    confirmCloses: int = 1
    #: ``close`` = market po prieraze, ``retest`` = po prieraze limitka na VAH / VAL platná `retestBars` barov.
    entryMode: EntryMode = EntryMode.CLOSE
    retestBars: int = 10
    # ---- 🧭 Filtre ------------------------------------------------------------ #
    #: Long len nad VWAP, short len pod (VWAP obchodného dňa od 18:00 NY, ako Pine `ta.vwap` na ETH grafe).
    useVwap: bool = False
    #: Šírka value area (VAH − VAL) v bodoch; 0 = bez hranice. Mimo hraníc sa v ten deň neobchoduje.
    vaMinPoints: float = 0.0
    vaMaxPoints: float = 0.0
    #: Tvar profilu: long len pri P-profile (POC a VA hore, tenký chvost dole), short len pri b-profile.
    useShape: bool = False
    #: P: POC aspoň na `shapePocPct` % výšky rangeu (b: najviac na 100 − X %).
    shapePocPct: float = 60.0
    #: P: stred value area aspoň na `shapeVaPct` % výšky rangeu.
    shapeVaPct: float = 55.0
    #: P: v dolnej tretine rangeu najviac `shapeTailPct` % objemu (b: v hornej).
    shapeTailPct: float = 25.0
    #: EMA filter je obal vstupu (`trendFilter`, skupina Typ vstupu); tu len predvolená dĺžka 100.
    trendEmaLen: int = 100
    # ---- 🛡️ Stop a cieľ ----------------------------------------------------------- #
    rrRatio: float = 1.0
    #: Rezerva stopu za POC v tickoch.
    slBufferTicks: int = 4
    #: Najväčší stop v bodoch / v ATR (14) grafu; 0 = bez hranice. Platí menšia z oboch.
    maxSlPoints: float = 0.0
    maxSlAtr: float = 0.0
    #: Stop nad limit: ``skip`` = obchod vynechať, ``cap`` = skrátiť stop na limit.
    slCapMode: SlCap = SlCap.SKIP
    #: Zavrieť otvorenú pozíciu v čase `closeH:M` (New York).
    useCloseTime: bool = False
    closeH: int = 15
    closeM: int = 59
    # ---- 💰 Veľkosť ----------------------------------------------------------- #
    fixedQty: bool = False
    qty: float = 1.0
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------ #
    showLevels: bool = True
    # ---- rozšírenia portu ---------------------------------------------------- #
    leverage: float = 1.0

    @staticmethod
    def _m(h: int, m: int) -> int:
        return h * 60 + m

    @property
    def range_start(self) -> int:
        return self._m(self.rangeStartH, self.rangeStartM)

    @property
    def range_end(self) -> int:
        return self._m(self.rangeEndH, self.rangeEndM)

    @property
    def entry_end(self) -> int:
        return self._m(self.entryEndH, self.entryEndM)

    @property
    def close_time(self) -> int:
        return self._m(self.closeH, self.closeM)

    def _problems(self) -> Iterable[str]:
        if self.range_end <= self.range_start:
            yield "range: koniec musí byť po začiatku (v ten istý deň)"
        if self.entry_end <= self.range_end:
            yield "vstupy musia končiť po konci rangeu"
        if self.vaMaxPoints and self.vaMinPoints > self.vaMaxPoints:
            yield "šírka VA: minimum je väčšie ako maximum"
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
