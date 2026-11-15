"""`AsiaSweepEurConfig` — tie isté parametre ako `asiasweep` (`tradebot/strategies/asiasweep/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..asiasweep.config import AsiaSweepConfig

__all__ = ["AsiaSweepEurConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class AsiaSweepEurConfig(AsiaSweepConfig):
    """Config ASIA SWEEP 1.0 (6E) — polia, defaulty a kontroly dedí z predlohy."""
