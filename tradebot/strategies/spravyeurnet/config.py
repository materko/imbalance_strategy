"""`SpravyEurNetConfig` — tie isté parametre ako `spravy`; číta ich C# jadro (`tradebot/strategies/spravy/ports/csharp/SpravyConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..spravyeur.config import SpravyEurConfig

__all__ = ["SpravyEurNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SpravyEurNetConfig(SpravyEurConfig):
    """Config SPRÁVY EUR/USD (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
