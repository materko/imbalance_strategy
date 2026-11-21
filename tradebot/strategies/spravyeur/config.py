"""`SpravyEurConfig` — tie isté parametre ako `spravy` (`tradebot/strategies/spravy/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..spravy.config import SpravyConfig

__all__ = ["SpravyEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SpravyEurConfig(SpravyConfig):
    """Config SPRÁVY na EUR/USD — polia, defaulty a kontroly dedí z predlohy."""
