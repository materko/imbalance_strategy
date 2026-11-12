"""`SigmaMymNetConfig` — tie isté parametre ako `sigmamym`; číta ich C# jadro (`tradebot/strategies/sigma/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sigmamym.config import SigmaMymConfig

__all__ = ["SigmaMymNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SigmaMymNetConfig(SigmaMymConfig):
    """Config SIGMA BREAKOUT 1.0 MYM (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
