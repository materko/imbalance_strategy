"""`SweepEngulfBtcConfig` — tie isté parametre ako `sweepengulf` (`tradebot/strategies/sweepengulf/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sweepengulf.config import SweepEngulfConfig

__all__ = ["SweepEngulfBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SweepEngulfBtcConfig(SweepEngulfConfig):
    """Config SWEEPING ENGULF 1.0 na BTC — polia, defaulty a kontroly dedí z predlohy."""
