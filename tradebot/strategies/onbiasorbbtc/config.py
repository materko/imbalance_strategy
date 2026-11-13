"""`OnBiasOrbBtcConfig` — tie isté parametre ako `onbiasorb` (`tradebot/strategies/onbiasorb/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..onbiasorb.config import OnBiasOrbConfig

__all__ = ["OnBiasOrbBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class OnBiasOrbBtcConfig(OnBiasOrbConfig):
    """Config Overnight Bias ORB na BTC — polia, defaulty a kontroly dedí z predlohy."""
