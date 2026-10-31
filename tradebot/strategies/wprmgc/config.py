"""`WprMgcConfig` — tie isté parametre ako `wpr` (`tradebot/strategies/wpr/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..wpr.config import WprConfig

__all__ = ["WprMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class WprMgcConfig(WprConfig):
    """Config WILLIAMS %R LONG 1.0 na MGC — polia, defaulty a kontroly dedí z predlohy."""
