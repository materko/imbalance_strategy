"""`NocPonMymConfig` — tie isté parametre ako `nocpon` (`tradebot/strategies/nocpon/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..nocpon.config import NocPonConfig

__all__ = ["NocPonMymConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NocPonMymConfig(NocPonConfig):
    """Config NOC + PONDELOK 1.0 na MYM — polia, defaulty a kontroly dedí z predlohy."""
