"""Config stratégie SWEEPING ENGULF 1.0 — sviečka vyberie extrém predošlej a zavrie za jej opačný koniec.

Stratégia nemá Pine predlohu; je to zápis z videa LuxAlgo „I Backtested This Viral Trading Strategy“
(youtube.com/watch?v=oxZj1kSye-g, nástroj LuxAlgo Quant, „Sweeping Engulfs“):

  * **manipulácia** — nová sviečka (video: 4h) ide pod low predošlej sviečky (výber), ale **zavrie nad jej high**
    (pohltí ju) → long; nad high predošlej a zavretie pod jej low → short (`engulfMode` body = stačí za telo),
  * **predošlá sviečka** (`prevCandle`): video nastavenie „same direction“ = predošlá sviečka išla smerom
    manipulácie (pred long medvedia, pred short býčia) — `opposite` voči smeru obchodu; `any` = hocijaká,
  * **vstup** market na zavretí signálnej sviečky; kým beží obchod, nové signály sa neberú,
  * **stop** za extrém signálnej sviečky (`candle`, pôvodné video) alebo `atrMult` × ATR(`atrLen`) od vstupu (`atr`),
    **cieľ** `rrRatio` × stop (video 1:2),
  * **filter trendu EMA 200** (video ho zapína) je spoločný filter `trendFilter` — v profile zapnutý.
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

__all__ = ["SweepEngulfConfig", "EngulfMode", "PrevCandle", "SlMethod", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class EngulfMode(str, Enum):
    RANGE = "range"   # zavretie za high (low) predošlej sviečky — pohltí ju celú (video)
    BODY = "body"     # stačí zavretie za telo predošlej sviečky


class PrevCandle(str, Enum):
    OPPOSITE = "opposite"   # predošlá sviečka proti smeru obchodu (smerom manipulácie) — video „same direction“
    SAME = "same"           # predošlá sviečka v smere obchodu
    ANY = "any"             # hocijaká (video „mixed“)


class SlMethod(str, Enum):
    CANDLE = "candle"   # za low / high signálnej sviečky (extrém manipulácie)
    ATR = "atr"         # atrMult × ATR od vstupu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {"slBufferAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {"engulfMode": EngulfMode, "prevCandle": PrevCandle, "slMethod": SlMethod,
                                "tradeDirection": TradeDirection}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "atrLen": (2, 200), "atrMult": (0.1, 20.0), "rrRatio": (0.2, 20.0), "riskDollar": (0, 100000),
    "qty": (0.001, 1000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class SweepEngulfConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Výber extrému predošlej sviečky a pohltenie → market, stop za manipuláciu, cieľ RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS,
                                              **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                             **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES
                                                  | ENTRY_CONFIRM_FIELD_NAMES | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🕯️ Signál ------------------------------------------------------------ #
    engulfMode: EngulfMode = EngulfMode.RANGE
    prevCandle: PrevCandle = PrevCandle.OPPOSITE
    tradeDirection: TradeDirection = TradeDirection.BOTH
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------- #
    slMethod: SlMethod = SlMethod.CANDLE
    #: Pri `candle`: rezerva za extrémom sviečky.
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    atrLen: int = 14
    #: Pri `atr`: stop = toľko ATR od vstupu (video skúšalo 1,5 až 5).
    atrMult: float = 1.5
    rrRatio: float = 2.0
    # ---- 💰 Veľkosť ------------------------------------------------------------ #
    fixedQty: bool = True
    qty: float = 1.0
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------- #
    showSignals: bool = True
    # ---- rozšírenia portu ------------------------------------------------------ #
    leverage: float = 1.0

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
