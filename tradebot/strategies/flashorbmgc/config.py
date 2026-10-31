"""`FlashorbMgcConfig` — tie isté parametre ako `flashorb` (`tradebot/strategies/flashorb/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..flashorb.config import FlashorbConfig

__all__ = ["FlashorbMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class FlashorbMgcConfig(FlashorbConfig):
    """Config FLASH TRIGGER ORB 1.0 na MGC — polia, defaulty a kontroly dedí z predlohy."""
