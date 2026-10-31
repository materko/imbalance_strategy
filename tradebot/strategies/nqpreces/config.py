"""`NqprecEsConfig` — tie isté parametre ako `nqprec` (`tradebot/strategies/nqprec/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..nqprec.config import NqprecConfig

__all__ = ["NqprecEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NqprecEsConfig(NqprecConfig):
    """Config NQ PRECISION 1.0 na ES — polia, defaulty a kontroly dedí z predlohy."""
