"""`TksBtcConfig` — tie isté parametre ako `tks` (`tradebot/strategies/tks/config.py`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..tks.config import TksConfig

__all__ = ["TksBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class TksBtcConfig(TksConfig):
    """Config TKS 1.0 (BTC) — polia, defaulty a kontroly dedí z predlohy."""
