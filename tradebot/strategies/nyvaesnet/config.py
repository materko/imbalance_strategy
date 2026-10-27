"""`NyVaEsNetConfig` — tie isté parametre ako NY VA BREAKOUT ES; číta ich C# jadro (`tradebot/strategies/nyva/csharp/NyVaConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..nyvaes.config import NyVaEsConfig

__all__ = ["NyVaEsNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NyVaEsNetConfig(NyVaEsConfig):
    """Config NY VA BREAKOUT ES (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
