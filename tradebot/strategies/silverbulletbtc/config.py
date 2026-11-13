"""`SilverBulletBtcConfig` — tie isté parametre ako `silverbullet` (`tradebot/strategies/silverbullet/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..silverbullet.config import SilverBulletConfig

__all__ = ["SilverBulletBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SilverBulletBtcConfig(SilverBulletConfig):
    """Config Silver Bullet 1.0 na BTC — polia, defaulty a kontroly dedí z predlohy."""
