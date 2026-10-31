"""`IvbEsConfig` — tie isté parametre ako `ivb` (`tradebot/strategies/ivb/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ivb.config import IvbConfig

__all__ = ["IvbEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IvbEsConfig(IvbConfig):
    """Config IVB 1.0 na ES — polia, defaulty a kontroly dedí z predlohy."""
