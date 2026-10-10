"""Config stratégie INTRADAY 1.0 — smernica obchodovania Martina (iCloud SMERNICA-OBCHODOVANIA, 8. 10. 2026).

Postup zhora nadol, len NY seansa:

  * **daily bias** (`biasMode`): smer dňa z denných zavretí RTH — zavretie nad EMA (`biasEmaLen`), včerajšie
    zavretie vs predvčerajšie, alebo vypnuté (oba smery),
  * **likvidita v protismere** (`liqMode`): pri long biase „hľadáme nižšiu likviditu“ — `zone` (default): zóna
    vstupu leží pri / pod low predošlého RTH dňa (PDL; proximal ≤ PDL + `liqTolAtr`), cena teda pri ceste do zóny
    likviditu zoberie; `sweep`: PDL už bolo dnes (od 18:00 NY) zobraté; short zrkadlovo s PDH; `off` = bez podmienky,
  * **SD zóny 1H → 15m → 5m**: zóna = báza (1–`baseMaxBars` sviečok s malými telami) + silný odchod (impulz
    a zavretie za bázou aspoň o `legOutMinAtr` ATR toho TF). Proximal na tele bázy, distal na knôte.
    15m zóna sa berie len vnútri živej 1H zóny v smere biasu, 5m len vnútri živej 15m zóny,
  * **vstup** (`entryTF` = TF zóny vstupu, default 5m): limitka na proximal čerstvej zóny (`entryDepthPct` do hĺbky;
    0 = dotyk), alebo po dotyku sviečka odmietnutia (`entryModel` reject), len v okne 9:30–16:00 NY,
  * **stop** za distal zóny vstupu + `slBufferAtr`, **cieľ** `rrRatio` × stop alebo opačná likvidita (PDH pri longu),
  * bez trailingu a bez zatvárania na konci seansy (pravidlá testovania); `useExitTime` voliteľne.

Pomôcky zo smernice (trendovka, FIBO, nPOC) sú zatiaľ mimo — ďalšia verzia. Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_filter import (ENTRY_FILTER_CONSTRAINTS, ENTRY_FILTER_ENUMS, ENTRY_FILTER_FIELD_NAMES,
                                        EntryFilterFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["IntradayConfig", "BiasMode", "LiqMode", "EntryModel", "TpMode", "TradeDirection", "CONFIG_DIR",
           "ZONE_TFS"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: TF zón zhora nadol (minúty); vstupný TF je jeden z nich
ZONE_TFS: tuple[int, ...] = (60, 15, 5)


class BiasMode(str, Enum):
    EMA = "ema"        # zavretie RTH včera nad / pod EMA denných zavretí
    CLOSE2 = "close2"  # včerajšie zavretie nad / pod predvčerajším
    OFF = "off"        # bez biasu — oba smery


class LiqMode(str, Enum):
    ZONE = "zone"      # zóna vstupu leží pri likvidite v protismere (pri / pod PDL pri longu, pri / nad PDH pri shorte)
    SWEEP = "sweep"    # likvidita v protismere už bola dnes zobratá
    OFF = "off"


class EntryModel(str, Enum):
    TOUCH = "touch"    # limitka na proximal (dotyk)
    REJECT = "reject"  # po dotyku sviečka zavrie späť mimo zóny v smere obchodu → market


class TpMode(str, Enum):
    RR = "rr"                 # násobok stopu
    LIQUIDITY = "liquidity"   # opačná likvidita predošlého dňa (PDH pri longu, PDL pri shorte)


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {"liqTolAtr": "atr", "slBufferAtr": "atr", "legOutMinAtr": "atr", "impulseMinBodyAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {"biasMode": BiasMode, "liqMode": LiqMode, "entryModel": EntryModel,
                                "tpMode": TpMode, "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "biasEmaLen": (2, 200), "entryTF": (5, 60), "baseMaxBars": (1, 6), "baseMaxBodyPct": (10, 90),
    "impulseMinBodyPct": (30, 100), "legOutMaxBars": (1, 10), "zoneAge60": (1, 500), "zoneAge15": (1, 200),
    "zoneAge5": (1, 100), "entryDepthPct": (0, 100), "startH": (0, 23), "startM": (0, 59), "endH": (0, 23),
    "endM": (0, 59), "exitH": (0, 23), "exitM": (0, 59), "rrRatio": (0.2, 20.0), "minRR": (0.0, 10.0),
    "maxTradesPerDay": (1, 20), "atrLen": (2, 100), "riskDollar": (0, 100000), "qty": (0.001, 1000),
    "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class IntradayConfig(StrategyConfig, EntryFilterFields):
    """Daily bias + likvidita PDH/PDL → SD zóna 1H → 15m → 5m → limitka, len NY seansa."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_FILTER_FIELD_NAMES

    # ---- 🧭 Daily bias ------------------------------------------------------- #
    biasMode: BiasMode = BiasMode.EMA
    biasEmaLen: int = 20
    # ---- 💧 Likvidita predošlého dňa ------------------------------------------ #
    liqMode: LiqMode = LiqMode.ZONE
    #: Pri `zone`: proximal smie byť nad PDL (pod PDH) najviac o toľko ATR grafu.
    liqTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    # ---- 📦 SD zóny (rovnaké pravidlo na každom TF) ---------------------------- #
    #: TF zóny, na ktorej sa vstupuje: 60 = rovno 1H zóna, 15 = 15m v 1H, 5 = 5m v 15m v 1H.
    entryTF: int = 5
    baseMaxBars: int = 3
    #: Sviečka bázy má telo najviac toľko % svojho rozsahu.
    baseMaxBodyPct: float = 50.0
    #: Impulz (prvá sviečka odchodu): telo aspoň toľko % rozsahu a aspoň `impulseMinBodyAtr` ATR.
    impulseMinBodyPct: float = 60.0
    impulseMinBodyAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.8, "atr"))
    #: Silný odchod: do `legOutMaxBars` sviečok zavretie za bázou aspoň o toľko ATR toho TF.
    legOutMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    legOutMaxBars: int = 3
    #: Životnosť zón v hodinách podľa TF.
    zoneAge60: int = 120
    zoneAge15: int = 24
    zoneAge5: int = 8
    # ---- 🎯 Vstup ------------------------------------------------------------- #
    entryModel: EntryModel = EntryModel.TOUCH
    #: Hĺbka limitky do zóny od proximal v % výšky zóny (0 = dotyk proximal).
    entryDepthPct: float = 0.0
    #: Okno vstupov (čas New York) — NY seansa.
    startH: int = 9
    startM: int = 30
    endH: int = 16
    endM: int = 0
    maxTradesPerDay: int = 2
    tradeDirection: TradeDirection = TradeDirection.BOTH
    weekdaysOnly: bool = True
    # ---- 🛡️ Stop a cieľ -------------------------------------------------------- #
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 2.0
    #: Pri cieli na likviditu: ak je bližšie ako `minRR` × stop, obchod sa nerobí (0 = vypnuté).
    minRR: float = 1.0
    atrLen: int = 14
    #: Voliteľne zavrieť v čase (pravidlá testovania: vypnuté).
    useExitTime: bool = False
    exitH: int = 15
    exitM: int = 55
    # ---- 💰 Veľkosť ------------------------------------------------------------ #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------- #
    showZones: bool = True
    showLiquidity: bool = True
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

    @property
    def exit_minutes(self) -> int:
        return self.exitH * 60 + self.exitM

    def zone_age_h(self, tf: int) -> int:
        return {60: self.zoneAge60, 15: self.zoneAge15, 5: self.zoneAge5}[tf]

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if int(self.entryTF) not in ZONE_TFS:
            yield f"entryTF={self.entryTF} musí byť jeden z {ZONE_TFS}"
        start, end = self.window
        if end <= start:
            yield "okno vstupov: koniec musí byť po začiatku"
