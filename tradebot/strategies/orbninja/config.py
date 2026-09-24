"""`ORBNinjaConfig` — tie isté parametre ako ORB (`tradebot/strategies/orb/config.py`).

ORBNinja je prepis ORB s jadrom v C#; parametre, ich rozsahy aj profily sú zámerne zhodné,
aby sa behy dali porovnať jedna k jednej. Vlastná trieda existuje len preto, že registry
hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..orb.config import ORBConfig

__all__ = ["ORBNinjaConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class ORBNinjaConfig(ORBConfig):
    """Config ORBNinja — polia, defaulty a kontroly dedí z ORB; číta ich C# jadro
    (`csharp/TradeBot.Strategies/OrbNinja/OrbConfig.cs`)."""
