"""`DailyOpenBtcConfig` — tie isté parametre ako `dailyopen` (`tradebot/strategies/dailyopen/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..dailyopen.config import DailyOpenConfig

__all__ = ["DailyOpenBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class DailyOpenBtcConfig(DailyOpenConfig):
    """Config DAILY OPEN 1.0 na BTC — polia, defaulty a kontroly dedí z predlohy."""
