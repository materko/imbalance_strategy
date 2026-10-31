"""`SigmaEsConfig` — tie isté parametre ako `sigma` (`tradebot/strategies/sigma/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sigma.config import SigmaConfig

__all__ = ["SigmaEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SigmaEsConfig(SigmaConfig):
    """Config SIGMA BREAKOUT 1.0 na ES — polia, defaulty a kontroly dedí z predlohy."""
