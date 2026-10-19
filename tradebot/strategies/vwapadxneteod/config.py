"""`VwapAdxNetEodConfig` — tie isté parametre ako VWAP ADX Pullback (C# jadro) (`tradebot/strategies/vwapadxnet/config.py`).

Koniec obchodného dňa (15:59 New York) nie je parameter — je to vlastnosť tejto stratégie. Vlastná trieda existuje
len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..vwapadxnet.config import VwapAdxNetConfig

__all__ = ["VwapAdxNetEodConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class VwapAdxNetEodConfig(VwapAdxNetConfig):
    """Config VWAP ADX Pullback (C# jadro EOD) — polia, defaulty a kontroly dedí z predlohy."""
