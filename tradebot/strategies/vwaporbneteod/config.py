"""`VwapOrbNetEodConfig` — tie isté parametre ako VWAP ORB 1.5 (C# jadro) (`tradebot/strategies/vwaporbnet/config.py`).

Koniec obchodného dňa (15:59 New York) nie je parameter — je to vlastnosť tejto stratégie. Vlastná trieda existuje
len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..vwaporbnet.config import VwapOrbNetConfig

__all__ = ["VwapOrbNetEodConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class VwapOrbNetEodConfig(VwapOrbNetConfig):
    """Config VWAP ORB 1.5 (C# jadro EOD) — polia, defaulty a kontroly dedí z predlohy."""
