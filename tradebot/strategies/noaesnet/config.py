"""`NoaEsNetConfig` — tie isté parametre ako `noa`; číta ich C# jadro (`tradebot/strategies/noa/ports/csharp/NoaConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..noaes.config import NoaEsConfig

__all__ = ["NoaEsNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NoaEsNetConfig(NoaEsConfig):
    """Config NOA 1.0 ES (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
