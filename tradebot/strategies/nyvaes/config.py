"""`NyVaEsConfig` — tie isté parametre ako NY VA BREAKOUT (`tradebot/strategies/nyva/config.py`).

Vlastná trieda existuje preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`), a aby
stratégia na NQ (`nyva`) ostala bez zásahu.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..nyva.config import NyVaConfig

__all__ = ["NyVaEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NyVaEsConfig(NyVaConfig):
    """Config NY VA BREAKOUT ES — polia, defaulty a kontroly dedí z NY VA BREAKOUT."""
