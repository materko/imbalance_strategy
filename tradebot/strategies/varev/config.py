"""Config stratégie VALUE AREA REVERSION 1.0 — únik z value area so slabnúcim objemom a návrat dnu.

Stratégia nemá Pine predlohu; je to zápis z videa LuxAlgo „I Turned A 4x World Cup Trader's Strategy Into An
Indicator“ (youtube.com/watch?v=dUczefIYKIU, indikátor „Value Area Reversion Signals“), podľa stratégie
Fabia Valentiniho (viacnásobné top 3 v Robbins World Cup Trading Championship):

  * **profil** — objemový profil futures seansy od 18:00 do 18:00 New York (`profileSession` ny = len NY seansa
    9:30–16:00, pri previous tá z predošlého dňa — zadanie Martina 10. 10. 2026) (`profileRows` riadkov, objem sviečky sa
    rozdelí rovnomerne do riadkov, ktorých sa dotkla — ako LuxAlgo), value area `valueAreaPct` % okolo POC;
    `profileSource` previous = profil predošlej dokončenej seansy (vo videu čistejšie signály), current = rozvíjajúci
    sa profil dnešnej seansy (z barov pred aktuálnym),
  * **únik** — sviečka zavrie pod VAL (long setup) / nad VAH (short setup),
  * **slabnúci objem** — objem sviečok v smere úniku klesá (`requireVolDecline`: posledná medvedia sviečka mimo
    value area má menší objem ako predošlá medvedia); medvedí / býčí objem = smer sviečky (graf nemá bid / ask),
  * **návrat** — do `maxBarsOutside` barov od úniku (video: 5) zavrie sviečka späť vo value area, je v smere obchodu
    a jej objem je väčší ako objem poslednej sviečky úniku (× `reclaimVolMult`); voliteľne pohltí telo predošlej
    sviečky (`requireEngulf`, filter z videa),
  * **vstup** market na zavretí, **stop** pod low úniku (+ `slBufferAtr`), **cieľ** opačná hrana value area (VAH pri
    longu), voliteľne POC alebo RR. Kým beží obchod, nové signály sa neberú.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["VaRevConfig", "ProfileSession", "ProfileSource", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class ProfileSource(str, Enum):
    PREVIOUS = "previous"   # profil predošlej dokončenej seansy 18:00–18:00 (video: čistejšie)
    CURRENT = "current"     # rozvíjajúci sa profil dnešnej seansy (z barov pred aktuálnym)


class ProfileSession(str, Enum):
    GLOBEX = "globex"   # celá futures seansa od `anchorH` (18:00) do 18:00 — video
    NY = "ny"           # len NY seansa `nyStartH:nyStartM`–`nyEndH:nyEndM` (9:30–16:00)


class TpMode(str, Enum):
    VA = "va"     # opačná hrana value area (VAH pri longu) — video
    POC = "poc"   # point of control
    RR = "rr"     # násobok stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {"slBufferAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {"profileSession": ProfileSession, "profileSource": ProfileSource, "tpMode": TpMode,
                                "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "anchorH": (0, 23), "nyStartH": (0, 23), "nyStartM": (0, 59), "nyEndH": (0, 23), "nyEndM": (0, 59),
    "profileRows": (10, 300), "valueAreaPct": (50.0, 99.0), "maxBarsOutside": (1, 50),
    "reclaimVolMult": (0.0, 10.0), "maxTradesPerDay": (1, 50), "startH": (0, 23), "startM": (0, 59),
    "endH": (0, 23), "endM": (0, 59), "atrLen": (2, 100), "rrRatio": (0.2, 20.0), "minRR": (0.0, 20.0),
    "riskDollar": (0, 100000), "qty": (0.001, 1000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class VaRevConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Únik pod VAL / nad VAH so slabnúcim objemom → návrat do value area so silným objemom → cieľ opačná hrana."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📊 Profil ----------------------------------------------------------- #
    profileSource: ProfileSource = ProfileSource.PREVIOUS
    #: Z akých barov je profil: globex = 18:00–18:00 (video), ny = len NY seansa (pri previous: NY seansa predošlého dňa).
    profileSession: ProfileSession = ProfileSession.GLOBEX
    #: Začiatok seansy profilu (hodina New York) — futures otvárajú o 18:00.
    anchorH: int = 18
    #: NY seansa profilu pri `profileSession` ny (čas New York, začiatok baru).
    nyStartH: int = 9
    nyStartM: int = 30
    nyEndH: int = 16
    nyEndM: int = 0
    profileRows: int = 60
    valueAreaPct: float = 70.0
    # ---- 🔁 Signál ------------------------------------------------------------ #
    #: Návrat do value area najviac toľko barov po úniku (video: 5).
    maxBarsOutside: int = 5
    requireVolDecline: bool = True
    #: Objem sviečky návratu aspoň toľkokrát objem poslednej sviečky úniku (0 = bez podmienky).
    reclaimVolMult: float = 1.0
    requireEngulf: bool = False
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 3
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    startH: int = 9
    startM: int = 30
    endH: int = 16
    endM: int = 0
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------- #
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    atrLen: int = 14
    tpMode: TpMode = TpMode.VA
    rrRatio: float = 2.0
    #: Bližší cieľ ako toľko × stop = bez obchodu (0 = vypnuté).
    minRR: float = 0.0
    # ---- 💰 Veľkosť ------------------------------------------------------------ #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------- #
    showValueArea: bool = True
    showPoc: bool = False
    showSignals: bool = True
    # ---- rozšírenia portu ------------------------------------------------------ #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def window(self) -> tuple[int, int]:
        return self.startH * 60 + self.startM, self.endH * 60 + self.endM

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.nyEndH * 60 + self.nyEndM <= self.nyStartH * 60 + self.nyStartM:
            yield "NY seansa profilu: koniec musí byť po začiatku"
        start, end = self.window
        if self.useTradeWindow and end <= start:
            yield "okno vstupov: koniec musí byť po začiatku"
