"""`SigmaMgcNetConfig` — tie isté parametre ako `sigmamgc`; číta ich C# jadro (`tradebot/strategies/sigma/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..sigmamgc.config import SigmaMgcConfig

__all__ = ["SigmaMgcNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class SigmaMgcNetConfig(SigmaMgcConfig):
    """Config SIGMA BREAKOUT 1.0 MGC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
