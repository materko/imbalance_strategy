"""`FvgPolarityMgcConfig` — tie isté parametre ako FVG POLARITY (`tradebot/strategies/fvgpolarity/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..fvgpolarity.config import FvgPolarityConfig

__all__ = ["FvgPolarityMgcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class FvgPolarityMgcConfig(FvgPolarityConfig):
    """Config FVG POLARITY na MGC — polia, defaulty a kontroly dedí z predlohy."""
