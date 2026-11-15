"""`LliqEurConfig` — tie isté parametre ako `lliq` (`tradebot/strategies/lliq/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..lliq.config import LliqConfig

__all__ = ["LliqEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class LliqEurConfig(LliqConfig):
    """Config LONDON LIQUIDITY IFVG 1.0 (6E) — polia, defaulty a kontroly dedí z predlohy."""
