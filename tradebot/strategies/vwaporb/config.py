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
from pathlib import Path
from typing import ClassVar

from tradebot.core.types import SizeSpec, SizeUnit

from ..orb.config import (CONSTRAINTS as ORB_CONSTRAINTS, ENUM_FIELDS as ORB_ENUM_FIELDS,
                          ORBConfig, SessionMode, SIZE_FIELDS as ORB_SIZE_FIELDS)
from ..vwapdrift.config import VwapAnchor, VwapPeriod

__all__ = ["VwapOrbConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {**ORB_SIZE_FIELDS, "vwapBreakAtr": "atr"}
ENUM_FIELDS: dict[str, type] = {**ORB_ENUM_FIELDS, "vwapAnchor": VwapAnchor, "vwapPeriod": VwapPeriod}
CONSTRAINTS: dict[str, tuple[float, float]] = {**ORB_CONSTRAINTS, "vwapBreakAtr": (0.0, 5.0)}


@dataclass
class VwapOrbConfig(ORBConfig):
    """ORB + prerazenie VWAP za range. Defaulty ORB zmenené len tam, kde by bránili zadaniu."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS

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
    #: O koľko musí byť VWAP za hranicou rangu, aby to bolo prerazenie (0 = stačí za ňou).
    vwapBreakAtr: SizeSpec = field(default_factory=lambda: SizeSpec(0.0, "atr"))
    #: Cena musí byť aj za VWAP (long close nad VWAP), nielen za hranicou rangu.
    closeBeyondVwap: bool = False
    showVwap: bool = True
