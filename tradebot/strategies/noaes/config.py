"""`NoaEsConfig` — tie isté parametre ako `noa` (`tradebot/strategies/noa/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..noa.config import NoaConfig

__all__ = ["NoaEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NoaEsConfig(NoaConfig):
    """Config NOA 1.0 na ES — polia, defaulty a kontroly dedí z predlohy."""
