"""`RangeBtcConfig` — tie isté parametre ako `range` (`tradebot/strategies/range/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..range.config import RangeConfig

__all__ = ["RangeBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class RangeBtcConfig(RangeConfig):
    """Config Range Breakout na BTC — polia, defaulty a kontroly dedí z predlohy."""
