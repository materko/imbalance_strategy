"""`FiboMgcNetConfig` — tie isté parametre ako Fibo 1.0 (MGC); číta ich C# jadro (`tradebot/strategies/fibo/csharp/FiboConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..fibomgc.config import FiboMgcConfig

__all__ = ["FiboMgcNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class FiboMgcNetConfig(FiboMgcConfig):
    """Config Fibo 1.0 MGC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
