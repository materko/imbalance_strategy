"""`NoaMymNetConfig` — tie isté parametre ako `noa`; číta ich C# jadro (`tradebot/strategies/noa/ports/csharp/NoaConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..noamym.config import NoaMymConfig

__all__ = ["NoaMymNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NoaMymNetConfig(NoaMymConfig):
    """Config NOA 1.0 MYM (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
