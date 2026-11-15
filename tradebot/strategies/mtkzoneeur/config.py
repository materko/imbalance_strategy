"""`MtkZoneEurConfig` — tie isté parametre ako `mtkzone` (`tradebot/strategies/mtkzone/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkzone.config import MtkZoneConfig

__all__ = ["MtkZoneEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkZoneEurConfig(MtkZoneConfig):
    """Config MTK ZONE (6E) — polia, defaulty a kontroly dedí z predlohy."""
