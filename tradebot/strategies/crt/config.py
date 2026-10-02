"""Config stratégie CRT + TBS — Candle Range Theory s Turtle Body Soup.

Stratégia nemá Pine predlohu; je to zápis verejne popisovaného postupu (ICT komunita, napr.
indikátor „CRT+TBS" na TradingView):

  1. **akumulácia** — jedna sviečka vyššieho TF (`rangeTF`, default 4h, skladá sa z barov grafu)
     je range: jej high je CRH, low CRL,
  2. **manipulácia** — nasledujúca sviečka vyššieho TF jednu stranu rangu vyberie (cena ide nad
     CRH alebo pod CRL); pri TBS („turtle body soup") výber spraví sviečka grafu **telom** —
     zavrie za hranicou,
  3. **otočka** — cena sa vráti do rangu a na grafe príde vstupný model: `model1` (sviečka zavrie
     za predošlou), `cisd` (zavretie za otvorením posledného ťahu k extrému) alebo `mss_fvg`
     (prerazenie štruktúry s medzerou, limitka do medzery),
  4. **distribúcia** — obchod proti výberu: stop za extrém manipulácie, cieľ stred rangu alebo
     jeho opačný koniec (prípadne RR).

Sviečky vyššieho TF sa skladajú rovnako ako inde v repozitári (hranice podľa UTC), takže 4h
sviečky začínajú o 0, 4, 8, 12, 16 a 20 h UTC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar, Iterable

from tradebot.core.config import StrategyConfig
from tradebot.core.entry_confirm import (ENTRY_CONFIRM_CONSTRAINTS, ENTRY_CONFIRM_ENUMS, ENTRY_CONFIRM_FIELD_NAMES,
                                         EntryConfirmFields)
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                       EntryOrderFields)
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["CrtConfig", "SweepKind", "EntryModel", "TpMode", "TradeDirection", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


class SweepKind(str, Enum):
    BODY = "body"  # TBS: sviečka grafu zavrie za hranicou rangu (výber telom)
    WICK = "wick"  # klasický turtle soup: stačí, že cena hranicu prekročí
    ANY = "any"


class EntryModel(str, Enum):
    MODEL1 = "model1"    # sviečka v smere obchodu zavrie späť v rangu a za predošlou sviečkou
    CISD = "cisd"        # zavretie za otvorením posledného ťahu k extrému (change in state of delivery)
    MSS_FVG = "mss_fvg"  # prerazenie štruktúry s medzerou (FVG); limitka do medzery


class TpMode(str, Enum):
    MID = "mid"            # stred rangu (50 %)
    OPPOSITE = "opposite"  # opačný koniec rangu (CRL pri shorte, CRH pri longu)
    RR = "rr"              # násobok stopu


class TradeDirection(str, Enum):
    BOTH = "Both"
    LONG_ONLY = "Long only"
    SHORT_ONLY = "Short only"


SIZE_FIELDS: dict[str, SizeUnit] = {
    "rangeMinAtr": "atr",
    "rangeMaxAtr": "atr",
    "sweepMaxAtr": "atr",
    "slBufferAtr": "atr",
    "slBufferPoints": "abs",
    "minSlDistance": "pct",
}

ENUM_FIELDS: dict[str, type] = {
    "sweepKind": SweepKind,
    "entryModel": EntryModel,
    "tpMode": TpMode,
    "tradeDirection": TradeDirection,
}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "rangeTF": (2, 1440),
    "sweepWithinBars": (1, 10),
    "validBars": (1, 20),
    "keyLookback": (1, 200),
    "swingLen": (1, 20),
    "fvgValidBars": (1, 100),
    "atrLen": (2, 100),
    "maxTradesPerDay": (1, 50),
    "tradeStartH": (0, 23),
    "tradeStartM": (0, 59),
    "tradeEndH": (0, 23),
    "tradeEndM": (0, 59),
    "rrRatio": (0.2, 20.0),
    "minRR": (0.0, 20.0),
    "maxHoldBars": (0, 5000),
    "riskDollar": (0, 100000),
    "tickDollarValue": (0.01, 1000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"tickDollarValue", "leverage", "legacyPineSizing", "minSlDistance"})


@dataclass
class CrtConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields):
    """Range sviečky vyššieho TF, výber jednej strany (turtle soup) a obchod späť cez range."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS, **ENTRY_CONFIRM_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES

    # ---- 🕯️ Range (CRT) --------------------------------------------------- #
    rangeTF: int = 240
    #: Range sviečka: výška v ATR vyššieho TF (0 = bez limitu).
    rangeMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    rangeMaxAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: V koľkých sviečkach vyššieho TF po range sviečke musí prísť výber (klasika: hneď v ďalšej).
    sweepWithinBars: int = 1
    #: Koľko sviečok vyššieho TF po range sviečke smie setup čakať na vstup (2 = manipulácia + distribúcia).
    validBars: int = 2
    #: Čakať, kým manipulačná sviečka vyššieho TF zavrie späť v rangu; vstup až v ďalšej (distribučnej).
    requireHtfClose: bool = False
    #: Kontext: vyberaná hranica musí byť aj starým vrcholom / dnom za `keyLookback` sviečok vyššieho TF.
    requireOldHL: bool = False
    keyLookback: int = 6
    atrLen: int = 14
    # ---- 🐢 Výber (turtle soup) ------------------------------------------- #
    sweepKind: SweepKind = SweepKind.BODY
    #: Najväčší výbeh za hranicu v ATR grafu; ďalej to už nie je výber, ale prerazenie (0 = bez limitu).
    sweepMaxAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    # ---- 🎯 Vstup ---------------------------------------------------------- #
    entryModel: EntryModel = EntryModel.CISD
    swingLen: int = 2
    fvgValidBars: int = 6
    tradeDirection: TradeDirection = TradeDirection.BOTH
    maxTradesPerDay: int = 3
    # ---- 🚦 Filtre -------------------------------------------------------- #
    weekdaysOnly: bool = True
    useTradeWindow: bool = False
    tradeTZ: str = "America/New_York"
    tradeStartH: int = 2
    tradeStartM: int = 0
    tradeEndH: int = 16
    tradeEndM: int = 0
    # ---- 🛡️ Stop a cieľ --------------------------------------------------- #
    slBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.1, "atr"))
    slBufferPoints: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "abs"))
    tpMode: TpMode = TpMode.OPPOSITE
    rrRatio: float = 2.0
    #: Pri cieli mid / opposite: bližší cieľ než toľko R sa neobchoduje.
    minRR: float = 1.0
    maxHoldBars: int = 0
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    showRanges: bool = True
    showSweeps: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    tickDollarValue: float | None = None
    legacyPineSizing: bool = False
    minSlDistance: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "pct"))
    leverage: float = 1.0

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
        if self.legacyPineSizing and self.tickDollarValue is None:
            yield "legacyPineSizing vyžaduje zadaný tickDollarValue"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
        if self.useTradeWindow and self.window_end_minutes <= self.window_start_minutes:
            yield "obchodné okno: koniec musí byť za začiatkom"
        if self.validBars < self.sweepWithinBars:
            yield "validBars musí byť aspoň sweepWithinBars — inak setup zanikne skôr, než môže prísť výber"
        if self.rangeMaxAtr.value and self.rangeMinAtr.value > self.rangeMaxAtr.value:
            yield "rangeMinAtr musí byť najviac rangeMaxAtr"
