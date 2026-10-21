"""`FiboMgcConfig` — tie isté parametre ako Fibo 1.0 (`tradebot/strategies/fibo/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..fibo.config import FiboConfig

__all__ = ["FiboMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class FiboMgcConfig(FiboConfig):
    """Config Fibo 1.0 (MGC) — polia, defaulty a kontroly dedí z predlohy."""
