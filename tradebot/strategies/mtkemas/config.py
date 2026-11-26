"""Config MTK EMAS 1.0 — sledovanie trendu podľa kĺzavých priemerov (štúdia Mac mini 25. 11. 2026, iCloud KLZAKY-STUDIA).

Štúdia (~500 000 nastavení na MNQ, MGC, ES, MYM, BTC): pod 30m kríženie nefunguje, najlepšie 1h–4h, **len longy**
s filtrom EMA 200, lepší signál je často **cena × dlhý priemer** než kríženie dvoch priemerov, typ priemeru rozhoduje
málo a výstup (trailing ATR) viac než vstup. Pravidlá sú presne tie zo štúdie:

  * **signál** — `signalMode` price: zavretie prekríži priemer `slowLen`; cross: priemer `fastLen` prekríži `slowLen`
    (typ `maType`). Kríženie = znamienko rozdielu sa zmení z jedného nenulového na opačné,
  * **filter** — spoločný filter trendu (profily: `trendFilter` with, `trendEmaLen` 200 = long len nad EMA 200 toho
    istého TF; default vypnutý ako pri každej stratégii), smer `tradeDirection` (štúdia: len longy),
  * **vstup** — market na zavretí signálnej sviečky (plní sa na otvorení ďalšej),
  * **stop** — `slAtr` × ATR(`atrLen`) signálnej sviečky od vstupu,
  * **výstup** — opačné kríženie (`exitOnSignal`), trailing `trailAtr` × ATR od najlepšej ceny (aktivácia od
    `trailFromR` R), zámok na vstup pri +`beAtR` R, pevný cieľ `rrTarget` R (0 = bez cieľa).
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

__all__ = ["MtkEmasConfig", "MaType", "SignalMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class MaType(str, Enum):
    EMA = "ema"
    SMA = "sma"
    WMA = "wma"
    HMA = "hma"
    DEMA = "dema"
    TEMA = "tema"
    RMA = "rma"
    VWMA = "vwma"
    KAMA = "kama"


class SignalMode(str, Enum):
    PRICE = "price"    # zavretie × priemer slowLen
    CROSS = "cross"    # priemer fastLen × priemer slowLen


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {"maType": MaType, "signalMode": SignalMode, "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "fastLen": (1, 500), "slowLen": (2, 1000), "atrLen": (2, 200), "slAtr": (0.2, 20.0), "trailAtr": (0.0, 50.0),
    "trailFromR": (0.0, 20.0), "beAtR": (0.0, 20.0), "rrTarget": (0.0, 50.0), "qty": (0.001, 1000),
    "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class MtkEmasConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Kríženie kĺzavých priemerov, filter EMA 200, stop v ATR, trailing / zámok / cieľ."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📈 Priemery a signál ------------------------------------------------- #
    maType: MaType = MaType.EMA
    signalMode: SignalMode = SignalMode.CROSS
    fastLen: int = 9
    slowLen: int = 21
    tradeDirection: TradeDirection = TradeDirection.LONG_ONLY
    # ---- 🛡️ Stop a výstup ----------------------------------------------------- #
    atrLen: int = 14
    #: počiatočný stop = slAtr × ATR signálnej sviečky
    slAtr: float = 1.5
    #: trailing = trailAtr × ATR od najlepšej ceny od vstupu (0 = bez trailingu)
    trailAtr: float = 3.0
    #: trailing sa zapne až pri zisku trailFromR × R (0 = hneď)
    trailFromR: float = 0.0
    #: zámok: pri zisku beAtR × R ide stop na vstup (0 = vypnuté)
    beAtR: float = 0.0
    #: pevný cieľ v R (0 = bez cieľa — obchod končí stopom, trailingom alebo opačným krížením)
    rrTarget: float = 0.0
    #: opačné kríženie zavrie pozíciu
    exitOnSignal: bool = True
    # ---- 💰 Veľkosť ------------------------------------------------------------- #
    fixedQty: bool = False
    qty: float = 1.0
    riskDollar: float = 500.0
    # ---- rozšírenia portu --------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        if self.signalMode is SignalMode.CROSS and int(self.fastLen) >= int(self.slowLen):
            yield f"fastLen={self.fastLen} musí byť kratší než slowLen={self.slowLen}"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
