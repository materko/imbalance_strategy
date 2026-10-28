"""`M2EURConfig` — tie isté parametre ako M2 (`tradebot/strategies/m2/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..m2.config import M2Config

__all__ = ["M2EURConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class M2EURConfig(M2Config):
    """Config M2 na Euro FX 6E — polia, defaulty a kontroly dedí z predlohy."""
