"""`SdEurNetConfig` — tie isté parametre ako SD ZÓNY EURUSD; číta ich C# jadro (`tradebot/csharp/TradeBot.Strategies/SdEurNet/SdEurConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sdeur.config import SdEurConfig

__all__ = ["SdEurNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SdEurNetConfig(SdEurConfig):
    """Config SD ZÓNY EURUSD (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
