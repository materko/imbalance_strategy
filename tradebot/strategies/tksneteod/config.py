"""`TksNetEodConfig` — tie isté parametre ako TKS 1.0 (C# jadro) (`tradebot/strategies/tksnet/config.py`).

Koniec obchodného dňa (15:59 New York) nie je parameter — je to vlastnosť tejto stratégie. Vlastná trieda existuje
len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..tksnet.config import TksNetConfig

__all__ = ["TksNetEodConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class TksNetEodConfig(TksNetConfig):
    """Config TKS 1.0 (C# jadro EOD) — polia, defaulty a kontroly dedí z predlohy."""
