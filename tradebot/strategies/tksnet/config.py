"""`TksNetConfig` — tie isté parametre ako TKS 1.0 (`tradebot/strategies/tks/config.py`).

Parametre, rozsahy aj profily sú zámerne zhodné s predlohou, aby sa behy dali porovnať jedna k jednej;
číta ich C# jadro (`tradebot/strategies/tks/csharp/TksConfig.cs`). Vlastná trieda existuje len
preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..tks.config import TksConfig

__all__ = ["TksNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class TksNetConfig(TksConfig):
    """Config TKS 1.0 s jadrom v C# — polia, defaulty a kontroly dedí z predlohy."""
