"""Config stratégie SD ZÓNY EURUSD 1.0 — kvalitné supply / demand zóny a limitka pri prvom návrate.

Zadanie používateľa (26. 10. 2026, Euro FX futures 6E): signifikantné zóny, z ktorých cena impulzívne odišla,
limitka na hrane zóny pri prvom návrate, stop kúsok za zónou, cieľ 1 : 1 až 1 : 3; vstupy hlavne v Londýne,
zóny môžu byť z noci. Najdôležitejšia je kvalita zón:

  * **zóna** sa hľadá na vyššom TF `zoneTF` (default 1 h, skladá sa zo sviečok grafu): báza 1–`baseMaxBars`
    sviečok (knôt po knôt, najviac `baseMax` vysoká) na extréme posledných `extremeBars` sviečok,
  * **odchod**: do `depMaxBars` sviečok cena odíde od bázy aspoň o `depMin` (v ATR zóny) a bázu predtým
    neprerazí — zóna platí od zavretia sviečky, ktorá odchod dokončila (žiadny pohľad dopredu),
  * **kvalita**: čas vzniku bázy (`formStartH`–`formEndH`, noc), výška zóny `minZoneHeight`–`maxZoneHeight`,
  * **vstup**: limitka na bližšej hrane (alebo `entryDepthPct` % hĺbky zóny) len v okne `entryStart`–`entryEnd`
    (Londýn); prvý dotyk mimo okna zónu minie bez obchodu,
  * **stop** za vzdialenejšou hranou + `slBuffer` + 1 tick, **cieľ** `rrRatio` × riziko, najdlhšie `maxHoldHours`.

Pine predlohu stratégia nemá. Logiku do C# jadra prepisuje `tradebot/csharp/TradeBot.Strategies/SdEurNet` (kľúč `sdeurnet`).
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

__all__ = ["SdEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {
    "baseMax": "atr", "depMin": "atr", "minZoneHeight": "atr", "maxZoneHeight": "atr", "slBuffer": "atr",
}
ENUM_FIELDS: dict[str, type] = {}
CONSTRAINTS: dict[str, tuple[float, float]] = {
    "zoneTF": (5, 240), "atrLen": (2, 100), "baseMaxBars": (1, 6), "extremeBars": (0, 96), "depMaxBars": (1, 48),
    "zoneMaxHours": (1, 720), "formStartH": (0, 23), "formEndH": (0, 23),
    "entryStartH": (0, 23), "entryStartM": (0, 59), "entryEndH": (0, 23), "entryEndM": (0, 59),
    "entryDepthPct": (0.0, 100.0), "maxTradesPerDay": (0, 50), "rrRatio": (0.2, 10.0), "maxHoldHours": (0, 720),
    "qty": (0.001, 1000), "riskDollar": (0, 100000), "leverage": (1, 125),
}
PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class SdEurConfig(StrategyConfig, EntryOrderFields, EntryConfirmFields, EntryFilterFields):
    """Zóny na vyššom TF z noci, limitka na hrane pri prvom návrate v Londýne, stop za zónou, cieľ v RR."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS, **ENTRY_CONFIRM_ENUMS, **ENTRY_FILTER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS,
                                                              **ENTRY_CONFIRM_CONSTRAINTS, **ENTRY_FILTER_CONSTRAINTS}
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = (PORT_ONLY_FIELDS | ENTRY_ORDER_FIELD_NAMES | ENTRY_CONFIRM_FIELD_NAMES
                                                  | ENTRY_FILTER_FIELD_NAMES)

    # ---- 🧱 Zóna (vyšší TF) ----------------------------------------------------- #
    #: TF, na ktorom sa hľadajú zóny (minúty, násobok TF grafu); sviečky sa skladajú zo sviečok grafu.
    zoneTF: int = 60
    #: ATR zóny (Wilder, na `zoneTF`) — jednotka pre výšku zóny, odchod a rezervu stopu.
    atrLen: int = 14
    #: Báza = 1 až toľko sviečok `zoneTF`, knôt po knôt.
    baseMaxBars: int = 4
    #: Najväčšia výška bázy.
    baseMax: SizeSpec = field(default_factory=lambda: SizeSpec(3.0, "atr"))
    #: Báza musí byť extrémom (supply: vrchol, demand: dno) posledných toľkých sviečok `zoneTF` pred ňou; 0 = nie.
    extremeBars: int = 4
    #: Odchod: aspoň o toľko od bázy (supply: low pod spodnou hranou, demand: high nad hornou) ...
    depMin: SizeSpec = field(default_factory=lambda: SizeSpec(1.0, "atr"))
    #: ... najneskôr do toľkých sviečok `zoneTF` po báze, bez prerazenia bázy predtým.
    depMaxBars: int = 8
    #: Výška zóny min / max (0 = bez hranice).
    minZoneHeight: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    maxZoneHeight: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Zóna platí najdlhšie toľko hodín od potvrdenia.
    zoneMaxHours: int = 120
    #: Len zóny, ktorých posledná sviečka bázy sa otvorila v `formStartH` ≤ h < `formEndH` (New York, cez polnoc).
    useFormWindow: bool = True
    formStartH: int = 18
    formEndH: int = 2
    # ---- 🎯 Vstup ---------------------------------------------------------------- #
    allowLong: bool = True
    allowShort: bool = True
    #: Okno vstupu (New York): limitka čaká len v ňom; prvý dotyk zóny mimo neho zónu minie bez obchodu.
    entryStartH: int = 2
    entryStartM: int = 0
    entryEndH: int = 11
    entryEndM: int = 0
    #: Limitka v hĺbke zóny: 0 = bližšia hrana, 50 = stred.
    entryDepthPct: float = 0.0
    #: Najviac obchodov za deň (New York); 0 = bez limitu.
    maxTradesPerDay: int = 0
    # ---- 🛡️ Stop a cieľ ---------------------------------------------------------- #
    #: Rezerva stopu za vzdialenejšou hranou (+ vždy 1 tick).
    slBuffer: SizeSpec = field(default_factory=lambda: SizeSpec(0.25, "atr"))
    rrRatio: float = 1.5
    #: Otvorenú pozíciu zavrieť po toľkých hodinách; 0 = drží sa do stopu alebo cieľa.
    maxHoldHours: int = 48
    # ---- 💰 Veľkosť ---------------------------------------------------------------- #
    fixedQty: bool = False
    qty: float = 1.0
    riskDollar: float = 500.0
    # ---- 🎨 Vizualizácia ------------------------------------------------------------ #
    showZones: bool = True
    # ---- rozšírenia portu ------------------------------------------------------------ #
    leverage: float = 1.0

    @property
    def entry_start(self) -> int:
        return self.entryStartH * 60 + self.entryStartM

    @property
    def entry_end(self) -> int:
        return self.entryEndH * 60 + self.entryEndM

    def _problems(self) -> Iterable[str]:
        if self.entry_end == self.entry_start:
            yield "okno vstupu: začiatok a koniec sú rovnaké"
        if self.useFormWindow and self.formStartH == self.formEndH:
            yield "okno vzniku zóny: začiatok a koniec sú rovnaké"
        if not (self.allowLong or self.allowShort):
            yield "povoľ aspoň jeden smer (allowLong alebo allowShort)"
        if self.maxZoneHeight.value > 0 and self.minZoneHeight.unit == self.maxZoneHeight.unit \
                and self.minZoneHeight.value > self.maxZoneHeight.value:
            yield "výška zóny: minimum je väčšie ako maximum"
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
