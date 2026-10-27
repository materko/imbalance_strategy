"""`VwapAdxNetConfig` — tie isté parametre ako VWAP ADX Pullback (`tradebot/strategies/vwapadx/config.py`).

Parametre, rozsahy aj profily sú zámerne zhodné s predlohou, aby sa behy dali porovnať jedna k jednej;
číta ich C# jadro (`tradebot/csharp/TradeBot.Strategies/VwapAdxNet/VwapAdxConfig.cs`). Vlastná trieda existuje len
preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..vwapadx.config import VwapAdxConfig

__all__ = ["VwapAdxNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class VwapAdxNetConfig(VwapAdxConfig):
    """Config VWAP ADX Pullback s jadrom v C# — polia, defaulty a kontroly dedí z predlohy."""
