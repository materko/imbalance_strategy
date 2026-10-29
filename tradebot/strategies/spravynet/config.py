"""`SpravyNetConfig` — tie isté parametre ako SPRÁVY; číta ich C# jadro (`tradebot/strategies/spravy/ports/csharp/SpravyConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..spravy.config import SpravyConfig

__all__ = ["SpravyNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SpravyNetConfig(SpravyConfig):
    """Config SPRÁVY (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
