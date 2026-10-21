"""`Scalp3MaMgcConfig` — tie isté parametre ako Scalping 3MA (`tradebot/strategies/scalp3ma/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..scalp3ma.config import Scalp3MaConfig

__all__ = ["Scalp3MaMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class Scalp3MaMgcConfig(Scalp3MaConfig):
    """Config Scalping 3MA (MGC) — polia, defaulty a kontroly dedí z predlohy."""
