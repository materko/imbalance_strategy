"""`IbRetMgcNetConfig` — tie isté parametre ako `ibret`; číta ich C# jadro (`tradebot/strategies/ibret/ports/csharp/IbRetConfig.cs`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibretmgc.config import IbRetMgcConfig

__all__ = ["IbRetMgcNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IbRetMgcNetConfig(IbRetMgcConfig):
    """Config IB RETRACE 1.0 MGC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
