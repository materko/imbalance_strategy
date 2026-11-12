"""`WprMymNetConfig` — tie isté parametre ako `wprmym`; číta ich C# jadro (`tradebot/strategies/wpr/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..wprmym.config import WprMymConfig

__all__ = ["WprMymNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class WprMymNetConfig(WprMymConfig):
    """Config WILLIAMS %R LONG 1.0 MYM (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
