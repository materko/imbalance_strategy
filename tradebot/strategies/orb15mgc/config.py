"""`Orb15MgcConfig` — tie isté parametre ako `orb15` (`tradebot/strategies/orb15/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..orb15.config import Orb15Config

__all__ = ["Orb15MgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class Orb15MgcConfig(Orb15Config):
    """Config ORB 15/5 1.0 na MGC — polia, defaulty a kontroly dedí z predlohy."""
