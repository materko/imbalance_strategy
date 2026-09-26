"""`IBSFvgConfig` — polia IBS Entry Zone, iné sú len defaulty zdrojov zón a entry modelov.

Zóny vznikajú len z FVG a IFVG. S/R, likvidita a Elliott sú natvrdo vypnuté; SD zóny
a engulfing sú vypnuté len defaultom a dajú sa zapnúť profilom — logika je tá istá ako v `ibsentry`, takže by to bol len iný názov pre
IBS Entry Zone. Vlastná trieda existuje, lebo registry hľadá stratégiu podľa triedy configu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibsentry.config import IBSEntryZoneConfig

__all__ = ["IBSFvgConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSFvgConfig(IBSEntryZoneConfig):
    """Config IBS FVG + IFVG — obchoduje len zóny z imbalance a ich inverzie."""

    enableZoneDetection: bool = False
    enableSrTrading: bool = False
    enableLqTrading: bool = False
    enableEngulfingEntry: bool = False
    enableFvgTrading: bool = True
    enableIfvgTrading: bool = True
    showSR: bool = False
    showLiqSweep: bool = False
    showElliott: bool = False

    def __post_init__(self) -> None:
        # S/R, likvidita a Elliott v tejto stratégii nie sú — ani z profilu inej stratégie.
        self.enableSrTrading = self.enableLqTrading = False
        self.showSR = self.showLiqSweep = self.showElliott = False
        super().__post_init__()
