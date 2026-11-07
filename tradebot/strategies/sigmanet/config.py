"""`SigmaNetConfig` — tie isté parametre ako `sigma`; číta ich C# jadro (`tradebot/strategies/sigma/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sigma.config import SigmaConfig

__all__ = ["SigmaNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SigmaNetConfig(SigmaConfig):
    """Config SIGMA BREAKOUT 1.0 (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
