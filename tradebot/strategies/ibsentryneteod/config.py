"""`IBSEntryNetEodConfig` — tie isté parametre ako IBS Entry Zone (C# jadro) (`tradebot/strategies/ibsentrynet/config.py`).

Koniec obchodného dňa (15:59 New York) nie je parameter — je to vlastnosť tejto stratégie. Vlastná trieda existuje
len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibsentrynet.config import IBSEntryNetConfig

__all__ = ["IBSEntryNetEodConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSEntryNetEodConfig(IBSEntryNetConfig):
    """Config IBS Entry Zone (C# jadro EOD) — polia, defaulty a kontroly dedí z predlohy."""
