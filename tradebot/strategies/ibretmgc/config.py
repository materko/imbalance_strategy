"""`IbRetMgcConfig` — tie isté parametre ako `ibret` (`tradebot/strategies/ibret/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibret.config import IbRetConfig

__all__ = ["IbRetMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IbRetMgcConfig(IbRetConfig):
    """Config IB RETRACE 1.0 (MGC) — polia, defaulty a kontroly dedí z predlohy."""
