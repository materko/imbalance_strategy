"""Config stratégie METODA 2 (M2) 1.0 — posledná opačná sviečka pred pohybom, potvrdenie telom, limitka na jej hrane.

Podľa podkladov používateľa (28. 10. 2026: `METODA_2.pdf`, `LTA - metoda2.pdf`, `m2 - advanced`):

  * **M2 long** = posledná **negatívna** sviečka pred pohybom hore; negatívna = zavretie pod 50 % jej rozsahu
    (farba nerozhoduje); **M2 short** = posledná **pozitívna** sviečka (zavretie nad 50 %) pred pohybom dole,
  * **potvrdenie**: neskoršia sviečka zavrie **celým telom** nad M2 (long: min(open, close) > high M2;
    short: max(open, close) < low M2),
  * **vstup**: po potvrdení limitka na **high M2** (long) / **low M2** (short), čaká sa na pullback,
  * **stop** pod low M2 (long) / nad high M2 (short) + `slTicks` tickov, **cieľ** `rrRatio` × riziko
    (podklad: „target do trendu 3 : 1“, advanced skalp fixne 2 : 1),
  * **trend** (advanced, ES 1m): EMA 20 / 200 / 300 / 600 / 1200 zoradené jedným smerom (`useEmaTrend`),
  * setup zaniká, keď sviečka zavrie za stopom bez vyplnenia, keď ho nahradí novšia potvrdená M2,
    alebo (voliteľne) po `limitMaxBars` sviečkach.

Pine predlohu stratégia nemá. Časti s order flow (absorpcia, delta, VPOC sviečky) sa z 1m OHLCV dát urobiť nedajú.
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

__all__ = ["M2Config", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "ema1": (1, 5000), "ema2": (1, 5000), "ema3": (1, 5000), "ema4": (1, 5000), "ema5": (1, 5000),
    "slTicks": (0, 1000), "rrRatio": (0.5, 20.0), "limitMaxBars": (0, 10000),
    "entryStartH": (0, 23), "entryStartM": (0, 59), "entryEndH": (0, 23), "entryEndM": (0, 59),
    "maxTradesPerDay": (0, 100), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class M2Config(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """M2 — order block posledná opačná sviečka, potvrdenie celým telom, limitka na hrane, stop za M2, cieľ RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📈 Trend (advanced: EMA zoradené jedným smerom) -------------------------- #
    useEmaTrend: bool = True
    #: Dĺžky EMA od najkratšej po najdlhšiu (advanced, ES 1m: 20 / 200 / 300 / 600 / 1200).
    ema1: int = 20
    ema2: int = 200
    ema3: int = 300
    ema4: int = 600
    ema5: int = 1200
    #: Long len keď je aj zavretie nad najkratšou EMA (short pod ňou).
    emaNeedClose: bool = False
    # ---- 🎯 Vstup ----------------------------------------------------------------- #
    allowLong: bool = True
    allowShort: bool = True
    #: Limitka čaká najviac toľko sviečok po potvrdení; 0 = kým setup nezanikne (stop / novšia M2).
    limitMaxBars: int = 0
    #: Okno vstupu (New York); vypnuté = celý deň.
    useWindow: bool = False
    entryStartH: int = 9
    entryStartM: int = 30
    entryEndH: int = 16
    entryEndM: int = 0
    #: Najviac obchodov za deň (New York); 0 = bez limitu.
    maxTradesPerDay: int = 0
    # ---- 🛡️ Stop a cieľ ----------------------------------------------------------- #
    #: Stop toľko tickov za druhým koncom M2 (pod low pri longu).
    slTicks: int = 1
    rrRatio: float = 2.0
    # ---- 💰 Veľkosť ---------------------------------------------------------------- #
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------------- #
    showZones: bool = True
    # ---- rozšírenia portu ------------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def emas(self) -> tuple[int, ...]:
        return (int(self.ema1), int(self.ema2), int(self.ema3), int(self.ema4), int(self.ema5))

    @property
    def entry_start(self) -> int:
        return self.entryStartH * 60 + self.entryStartM

    @property
    def entry_end(self) -> int:
        return self.entryEndH * 60 + self.entryEndM

    def _problems(self) -> Iterable[str]:
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        if self.useWindow and self.entry_end == self.entry_start:
            yield "okno vstupu: začiatok a koniec sú rovnaké"
        if list(self.emas) != sorted(self.emas):
            yield "EMA musia ísť od najkratšej po najdlhšiu (ema1 ≤ ema2 ≤ … ≤ ema5)"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
