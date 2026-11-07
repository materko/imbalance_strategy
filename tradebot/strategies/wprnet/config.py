"""`WprNetConfig` — tie isté parametre ako `wpr`; číta ich C# jadro (`tradebot/strategies/wpr/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..wpr.config import WprConfig

__all__ = ["WprNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class WprNetConfig(WprConfig):
    """Config WILLIAMS %R LONG 1.0 (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
