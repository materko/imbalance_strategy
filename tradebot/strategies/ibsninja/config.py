"""`IBSNinjaConfig` — tie isté parametre ako IBS (`tradebot/strategies/ibs/config.py`).

IBSNinja je prepis IBS s jadrom v C#; parametre, ich rozsahy aj profily sú zámerne zhodné,
aby sa behy dali porovnať jedna k jednej. Vlastná trieda existuje len preto, že registry
hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibs.config import IBSConfig

__all__ = ["IBSNinjaConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IBSNinjaConfig(IBSConfig):
    """Config IBSNinja — polia, defaulty a kontroly dedí z IBS; číta ich C# jadro
    (`csharp/TradeBot.Strategies/IbsNinja/IbsConfig.cs`)."""
