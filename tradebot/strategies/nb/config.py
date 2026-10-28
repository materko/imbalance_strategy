"""Config stratégie NB 1.0 — prieraz konsolidácie na grafe v smere trendu vyššieho TF (SMA 10 / 20).

Podľa videa TradeCZ s traderkou Nikolou (YouTube KBCvpjMWd5A, 2026), zadanie používateľa 28. 10. 2026:

  * **trend** na vyššom TF `htfTF` (default H4, skladá sa zo sviečok grafu): SMA `smaFast` nad SMA `smaSlow`
    (a voliteľne zavretie nad rýchlou) = uptrend → len longy; zrkadlovo downtrend → len shorty,
  * **konsolidácia** na grafe (default M15): posledných `consBars` sviečok vrátane knôtov je široké
    `consMinWidth`–`consMaxWidth` (v ATR grafu) — trh nemá smer,
  * **vstup** stop orderom hneď pri prieraze hrany konsolidácie v smere trendu (nečaká sa na zavretie sviečky),
    len keď je aj na grafe cena na tej istej strane oboch SMA a rýchla je za pomalou („SMA ukážu smer"),
  * **stop** za opačnou hranou konsolidácie + `slBuffer` + 1 tick, **cieľ** `rrRatio` × riziko (default 3),
  * **miesto do cieľa** (`useRoom`): najbližší swing vyššieho TF v smere obchodu musí byť aspoň `roomMinR` R
    od vstupu, inak sa obchod vynechá (Nikola: „pod 2,5 R obchod neberiem"),
  * čas (New York) `entryStartH:M`–`entryEndH:M`, dni v týždni, najviac `maxTradesPerDay` obchodov za deň.

Pine predlohu stratégia nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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

__all__ = ["NbConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {"consMinWidth": "atr", "consMaxWidth": "atr", "slBuffer": "atr"}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "htfTF": (15, 1440), "smaFast": (2, 200), "smaSlow": (2, 400), "atrLen": (2, 100),
    "consBars": (3, 100), "entryOffsetTicks": (0, 100), "pivotLen": (1, 10), "roomMinR": (0.0, 20.0),
    "entryStartH": (0, 23), "entryStartM": (0, 59), "entryEndH": (0, 23), "entryEndM": (0, 59),
    "maxTradesPerDay": (0, 50), "rrRatio": (0.5, 20.0), "maxHoldHours": (0, 720),
    "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class NbConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Prieraz konsolidácie na grafe v smere trendu vyššieho TF, stop za konsolidáciou, cieľ v RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 📈 Trend (vyšší TF) ------------------------------------------------------ #
    #: TF trendu v minútach (240 = H4); sviečky sa skladajú zo sviečok grafu.
    htfTF: int = 240
    #: Rýchla a pomalá SMA zo zavretí — na vyššom TF aj na grafe.
    smaFast: int = 10
    smaSlow: int = 20
    #: Filter trendu vyššieho TF: uptrend = rýchla SMA nad pomalou (downtrend zrkadlovo).
    useHtfTrend: bool = True
    #: ... a navyše posledné zavretie vyššieho TF nad rýchlou SMA (pod ňou pri downtrende).
    htfNeedClose: bool = True
    #: Na grafe: pri longu zavretie nad oboma SMA a rýchla nad pomalou (short zrkadlovo).
    useChartSma: bool = True
    # ---- 📦 Konsolidácia (graf) --------------------------------------------------- #
    #: Konsolidácia = posledných toľkých sviečok grafu (vrátane knôtov).
    consBars: int = 8
    #: ATR grafu (Wilder) — jednotka šírky konsolidácie a rezervy stopu.
    atrLen: int = 14
    #: Šírka konsolidácie (high − low okna) od–do; 0 = bez hranice.
    consMinWidth: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    consMaxWidth: SizeSpec = field(default_factory=lambda: SizeSpec(2.0, "atr"))
    # ---- 🎯 Vstup (čas New York) --------------------------------------------------- #
    allowLong: bool = True
    allowShort: bool = True
    #: Stop order toľko tickov za hranou konsolidácie (0 = presne na hrane).
    entryOffsetTicks: int = 1
    entryStartH: int = 2
    entryStartM: int = 0
    entryEndH: int = 16
    entryEndM: int = 0
    tradeMon: bool = True
    tradeTue: bool = True
    tradeWed: bool = True
    tradeThu: bool = True
    tradeFri: bool = True
    #: Najviac obchodov za deň (New York); 0 = bez limitu.
    maxTradesPerDay: int = 0
    # ---- 🛡️ Stop a cieľ ------------------------------------------------------------- #
    #: Rezerva stopu za opačnou hranou konsolidácie (+ vždy 1 tick); Nikola: 5 pipov.
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(0.25, "atr"))
    rrRatio: float = 3.0
    #: Miesto do cieľa: najbližší swing vyššieho TF v smere obchodu aspoň `roomMinR` R od vstupu.
    useRoom: bool = True
    roomMinR: float = 2.5
    #: Swing vyššieho TF = vrchol / dno, ktoré má po oboch stranách toľko sviečok nižšie / vyššie.
    pivotLen: int = 2
    #: Otvorenú pozíciu zavrieť po toľkých hodinách; 0 = drží sa do stopu alebo cieľa.
    maxHoldHours: int = 0
    # ---- 💰 Veľkosť ------------------------------------------------------------------ #
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia --------------------------------------------------------------- #
    showZones: bool = True
    # ---- rozšírenia portu --------------------------------------------------------------- #
    leverage: float = 1.0

    @property
    def entry_start(self) -> int:
        return self.entryStartH * 60 + self.entryStartM

    @property
    def entry_end(self) -> int:
        return self.entryEndH * 60 + self.entryEndM

    @property
    def weekdays(self) -> tuple[bool, ...]:
        """Pondelok … piatok (sobota a nedeľa = piatok / pondelok seansy sa neobchodujú zvlášť)."""
        return (self.tradeMon, self.tradeTue, self.tradeWed, self.tradeThu, self.tradeFri, False, False)

    def _problems(self) -> Iterable[str]:
        if self.entry_end == self.entry_start:
            yield "okno vstupu: začiatok a koniec sú rovnaké"
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        if self.smaFast >= self.smaSlow:
            yield f"smaFast={self.smaFast} musí byť kratšia ako smaSlow={self.smaSlow}"
        if self.consMaxWidth.value > 0 and self.consMinWidth.unit == self.consMaxWidth.unit \
                and self.consMinWidth.value > self.consMaxWidth.value:
            yield "šírka konsolidácie: minimum je väčšie ako maximum"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
