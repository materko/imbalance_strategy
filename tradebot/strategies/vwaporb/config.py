"""Config stratégie VWAP ORB 1.0 — ORB (New York opening range) so vstupom až po prerazení VWAP.

Všetky polia ORB (range, stop, cieľ, riziko) sa dedia z `tradebot/strategies/orb/config.py`;
tu sú len polia VWAP a defaulty, ktoré zo stratégie robia to, čo zadal tester (2026-09-28):

* obchoduje sa len **New York** range (od 9:30 NY = 15:30 SEČ),
* signál je, keď **VWAP** (od 9:30 NY, ten istý ako vo VWAP Session) prerazí nad high rangu
  (pod low) **a zároveň** je tam aj cena — close nad high (pod low); vstup market na zavretí,
* stop na opačnej strane rangu, cieľ RR.

ORB filtre, ktoré by ticho vyraďovali dni (šírka rangu, poloha close v sviečke, 90-minútové
okno), sú tu vypnuté: VWAP sa dostane za range často až neskôr počas dňa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar

from tradebot.core.types import SizeSpec, SizeUnit

from ..orb.config import (CONSTRAINTS as ORB_CONSTRAINTS, ENUM_FIELDS as ORB_ENUM_FIELDS,
                          ORBConfig, SessionMode, SIZE_FIELDS as ORB_SIZE_FIELDS)
from ..vwapdrift.config import VwapAnchor, VwapPeriod
from tradebot.core.entry_order import (ENTRY_ORDER_CONSTRAINTS, ENTRY_ORDER_ENUMS, ENTRY_ORDER_FIELD_NAMES,
                                          EntryOrderFields)

__all__ = ["VwapOrbConfig", "VwapRule", "ExitMode", "EntryTiming", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

class VwapRule(str, Enum):
    """Čo musí VWAP spraviť, aby prerazenie rangu cenou bolo signálom.

    * ``break``     — VWAP prerazí za range (long nad high, short pod low) a cena je tam tiež
    * ``direction`` — stačí prerazenie rangu cenou; VWAP len smeruje rovnako (long stúpa,
                      short klesá) — zmena za ``vwapDriftBars`` periód aspoň ``vwapDriftMinAtr``
    """

    BREAK = "break"
    DIRECTION = "direction"


class EntryTiming(str, Enum):
    """Kedy sa smie vstúpiť.

    * ``any``          — prvá sviečka, na ktorej platí prerazenie rangu cenou aj podmienka VWAP
                         (môže prísť aj hodinu po prerazení, kým VWAP dôjde)
    * ``break_candle`` — len prerazovacia sviečka (prvá, ktorá zavrie za range); podmienka VWAP
                         sa vyhodnotí na nej a keď nesedí, v tom smere sa v ten deň nevstupuje.
                         Smer VWAP sa berie z toľkých periód, koľko ich je (15m VWAP má o 9:50
                         len jednu); keď nie je ani jedna, z VWAP barov grafu. Dáva zmysel
                         s ``vwapRule=direction`` — pri ``break`` je VWAP v momente prerazenia
                         takmer vždy ešte vnútri rangu
    """

    ANY = "any"
    BREAK_CANDLE = "break_candle"


class ExitMode(str, Enum):
    """Ako sa obchod končí (stop na opačnej strane rangu platí vždy).

    * ``tp``      — cieľ podľa ORB (``tpMode``, štandardne RR)
    * ``vwap``    — bez pevného cieľa: drží sa, kým cena od vstupu neprerazí VWAP proti obchodu
                    (long zavrie pod VWAP); cieľ je technicky 100R, aby ho adaptéry mali
    * ``tp_vwap`` — čo príde skôr: cieľ alebo prerazenie VWAP proti obchodu
    """

    TP = "tp"
    VWAP = "vwap"
    TP_VWAP = "tp_vwap"

    @property
    def vwap_exit(self) -> bool:
        return self is not ExitMode.TP


SIZE_FIELDS: dict[str, SizeUnit] = {**ORB_SIZE_FIELDS, "vwapBreakAtr": "atr", "vwapDriftMinAtr": "atr",
                                    "vwapExitAtr": "atr", "vwapStopAtr": "atr", "vwapTpAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {**ORB_ENUM_FIELDS, "vwapAnchor": VwapAnchor, "vwapPeriod": VwapPeriod,
                                "vwapRule": VwapRule, "exitMode": ExitMode,
                                "entryTiming": EntryTiming}
CONSTRAINTS: dict[str, tuple[float, float]] = {**ORB_CONSTRAINTS, "vwapBreakAtr": (0.0, 5.0),
                                               "vwapDriftBars": (1, 26), "vwapDriftMinAtr": (0.0, 5.0),
                                               "vwapExitAtr": (0.0, 5.0), "vwapStopAtr": (0.0, 5.0),
                                               "vwapTpAtr": (0.0, 5.0)}


@dataclass
class VwapOrbConfig(ORBConfig):
    """ORB + prerazenie VWAP za range. Defaulty ORB zmenené len tam, kde by bránili zadaniu."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = {**ENUM_FIELDS, **ENTRY_ORDER_ENUMS}
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = {**CONSTRAINTS, **ENTRY_ORDER_CONSTRAINTS}

    # ---- zmenené defaulty ORB -------------------------------------------- #
    sessionMode: SessionMode = SessionMode.NY
    breakBufferAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    entryWindowMinutes: int = 0
    minRangePct: float = 0.0
    maxRangePct: float = 10.0
    minClosePosPct: int = 0
    # ---- 📊 VWAP ---------------------------------------------------------- #
    vwapAnchor: VwapAnchor = VwapAnchor.NY_OPEN
    vwapPeriod: VwapPeriod = VwapPeriod.M15
    vwapRule: VwapRule = VwapRule.BREAK
    entryTiming: EntryTiming = EntryTiming.ANY
    #: O koľko musí byť VWAP za hranicou rangu, aby to bolo prerazenie (0 = stačí za ňou).
    vwapBreakAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Cena musí byť aj za VWAP (long close nad VWAP), nielen za hranicou rangu.
    closeBeyondVwap: bool = False
    #: Pri ``vwapRule=direction``: smer VWAP = zmena za toľko periód VWAP (15m sviečok, resp. barov).
    vwapDriftBars: int = 2
    vwapDriftMinAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    # ---- 🚪 Výstup cez VWAP ------------------------------------------------ #
    exitMode: ExitMode = ExitMode.TP
    #: O koľko musí cena zavrieť za VWAP proti obchodu, aby sa obchod zavrel (0 = stačí za ním).
    vwapExitAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Stop na VWAP: posúva sa s ním a obchod končí dotykom VWAP (aj knôtom). Vypnuté = stop ORB.
    vwapStop: bool = False
    vwapStopAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: TP na cross VWAP: keď je VWAP za vstupom v zisku, dotyk VWAP obchod zavrie (stop ostáva ORB).
    vwapTp: bool = False
    vwapTpAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    showVwap: bool = True
