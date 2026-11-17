"""`TksEurNetConfig` — tie isté parametre ako `tks`; číta ich C# jadro (`tradebot/strategies/tks/ports/csharp/TksConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..tkseur.config import TksEurConfig

__all__ = ["TksEurNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class TksEurNetConfig(TksEurConfig):
    """Config TKS 1.0 6E (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
