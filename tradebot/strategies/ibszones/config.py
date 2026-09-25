"""`IBSZonesConfig` — tie isté parametre ako IBS (`tradebot/strategies/ibs/config.py`).

IBSZones je IBS so synchronizovanou detekciou zón (`htf.py`); parametre, ich rozsahy aj
profily sú zámerne zhodné, aby sa behy dali porovnať jedna k jednej s `ibs` a bolo vidieť,
čo tá zmena spravila. Vlastná trieda existuje len preto, že registry hľadá stratégiu
podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibs.config import IBSConfig

__all__ = ["IBSZonesConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSZonesConfig(IBSConfig):
    """Config IBSZones — polia, defaulty aj kontroly dedí z IBS."""
