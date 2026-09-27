"""Config stratégie Liquidity — likvidita na swing vrcholoch a dnách, jej vybratie a cesta k nej.

Stratégia nemá Pine predlohu. Likvidita sa značí klasicky: z výrazného swing vrcholu (buy-side,
stopky nad ním) a dna (sell-side) sa ťahá vodorovná úroveň, kým ju cena nezoberie. Úrovne
sa značia naraz na viacerých TF (5m až 4h), ktoré si engine skladá z barov grafu. Rovnaké
vrcholy/dná sa zlúčia do jednej silnejšej úrovne.

Prahy sú v ATR (TF úrovne pre značenie, TF grafu pre vstup) alebo v percentách ceny.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["LiquidityConfig", "TradeMode", "EntryModel", "EntryOrder", "SlMode", "TpMode",
           "TradeDirection", "LIQ_TIMEFRAMES", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

#: TF, na ktorých sa likvidita značí — pole configu -> minúty.
LIQ_TIMEFRAMES: tuple[tuple[str, int], ...] = (
    ("liqUse5m", 5), ("liqUse15m", 15), ("liqUse30m", 30), ("liqUse60m", 60), ("liqUse240m", 240),
)


class TradeMode(str, Enum):
    """Čo je spúšťač obchodu."""

    SWEEP = "sweep"        # cena zoberie likviditu a zavrie späť -> obchod proti (otočka)
    BREAKOUT = "breakout"  # cena zoberie likviditu a zavrie za ňou -> pokračovanie k ďalšej
    DRAW = "draw"          # bez udalosti: vstupný signál smerom k najbližšej nevybratej likvidite


class EntryModel(str, Enum):
    IMBALANCE = "imbalance"  # IBS: imbalance sviečka (medzera medzi 1. a 3. sviečkou) v smere
    PINBAR = "pinbar"        # pin bar — dlhý knôt proti smeru, telo na opačnom konci
    ANY = "any"              # imbalance alebo pin bar
    CLOSE = "close"          # hneď zavretie sviečky v smere (bez vzoru)


class EntryOrder(str, Enum):
    MARKET = "market"  # na zavretí signálnej sviečky
    LIMIT = "limit"    # limitka na stred signálnej sviečky (lepšia cena, nie každá sa vyplní)


class SlMode(str, Enum):
    LEVEL = "level"    # za extrém okolo likvidity (knôt sweepu / prerazená úroveň)
    SIGNAL = "signal"  # za signálnu sviečku
    SWING = "swing"    # za extrém posledných `slLookback` barov
    ATR = "atr"        # násobok ATR od vstupu


class TpMode(str, Enum):
    RR = "rr"                # násobok vzdialenosti SL
    LIQUIDITY = "liquidity"  # najbližšia nevybratá likvidita v smere obchodu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "liqMinDispAtr": "atr",
    "liqEqualTolAtr": "atr",
    "breakBufferAtr": "atr",
    "imbMinSizeAtr": "atr",
    "slBufferAtr": "atr",
    "slAtrMult": "atr",
    "tpOffsetAtr": "atr",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "tradeMode": TradeMode,
    "entryModel": EntryModel,
    "entryOrder": EntryOrder,
    "slMode": SlMode,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "liqPivotLen": (1, 30),
    "liqMaxAgeHours": (1, 2000),
    "liqMinStrength": (1, 5),
    "sweepBars": (1, 20),
    "setupMaxBars": (1, 50),
    "pbWickPct": (30, 95),
    "pbBodyPct": (5, 60),
    "maxTradesPerDay": (1, 50),
    "cooldownBars": (0, 100),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "atrLen": (2, 100),
    "slLookback": (1, 100),
    "rrRatio": (0.2, 10.0),
    "minRR": (0.0, 10.0),
    "maxRR": (0.0, 20.0),
    "maxHoldBars": (0, 1000),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset(
    {"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class LiquidityConfig(StrategyConfig):
    """Likvidita na viacerých TF, jej vybratie (sweep / prerazenie) a obchod k ďalšej likvidite."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 💧 Značenie likvidity -------------------------------------------- #
    liqUse5m: bool = False
    liqUse15m: bool = True
    liqUse30m: bool = False
    liqUse60m: bool = True
    liqUse240m: bool = False
    liqPivotLen: int = 5
    liqMinDispAtr: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    liqEqualTolAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.15, "atr"))
    liqMaxAgeHours: int = 120
    liqMinStrength: int = 1
    # ---- 🎯 Spúšťač a vstup ----------------------------------------------- #
    tradeMode: TradeMode = TradeMode.BREAKOUT
    tradeDirection: TradeDirection = TradeDirection.BOTH
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    sweepBars: int = 3
    entryModel: EntryModel = EntryModel.IMBALANCE
    entryOrder: EntryOrder = EntryOrder.MARKET
    setupMaxBars: int = 12
    imbMinSizeAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.2, "atr"))
    pbWickPct: int = 60
    pbBodyPct: int = 30
    maxTradesPerDay: int = 5
    cooldownBars: int = 3
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 9
    tradeStartM: int = 30
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    slMode: SlMode = SlMode.LEVEL
    atrLen: int = 14
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.2, "atr"))
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    slLookback: int = 5
    # ---- 🏁 Cieľ ---------------------------------------------------------- #
    tpMode: TpMode = TpMode.RR
    rrRatio: float = 1.5
    minRR: float = 1.0
    maxRR: float = 5.0
    tpOffsetAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    maxHoldBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showLevels: bool = True
    showEvents: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    #: Doslovný Pine vzorec veľkosti pozície vrátane `int()` + `max(1, …)` — len na porovnanie.
    legacyPineSizing: bool = False
    #: Minimálna vzdialenosť SL od vstupu, inak sa obchod preskočí. 0 = vypnuté.
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

    # ------------------------------------------------------------------ #

    def active_liq_timeframes(self) -> tuple[int, ...]:
        return tuple(m for name, m in LIQ_TIMEFRAMES if getattr(self, name))

    @property
    def allow_long(self) -> bool:
        return self.tradeDirection is not TradeDirection.SHORT_ONLY

    @property
    def allow_short(self) -> bool:
        return self.tradeDirection is not TradeDirection.LONG_ONLY

    @property
    def window_start_minutes(self) -> int:
        return self.tradeStartH * 60 + self.tradeStartM

    @property
    def window_end_minutes(self) -> int:
        return self.tradeEndH * 60 + self.tradeEndM

    def position_qty(self, inst, risk_amount: float, sl_distance: float) -> float:
        if self.legacyPineSizing:
            return inst.qty_for_risk_pine(risk_amount, sl_distance, self.tickDollarValue or 0.0)
        return inst.qty_for_risk(risk_amount, sl_distance)

    def _problems(self) -> Iterable[str]:
        if not self.active_liq_timeframes():
            yield "nie je zapnutý žiadny TF likvidity (liqUse5m … liqUse240m) — nie je čo obchodovať"
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.maxRR and self.minRR > self.maxRR:
            yield f"minRR={self.minRR} musí byť najviac maxRR={self.maxRR}"
        if self.pbBodyPct + self.pbWickPct > 100:
            yield f"pbWickPct + pbBodyPct = {self.pbWickPct + self.pbBodyPct} > 100 — pin bar nemôže vzniknúť"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
