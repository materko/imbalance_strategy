"""`IbRetNetConfig` — tie isté parametre ako IB RETRACE 1.0 (`tradebot/strategies/ibret/config.py`).

Parametre, rozsahy aj profily sú zámerne zhodné s predlohou, aby sa behy dali porovnať jedna k jednej;
číta ich C# jadro (`tradebot/strategies/ibret/ports/csharp/IbRetConfig.cs`). Vlastná trieda existuje len
preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..ibret.config import IbRetConfig

__all__ = ["IbRetNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class IbRetNetConfig(IbRetConfig):
    """Config IB RETRACE 1.0 s jadrom v C# — polia, defaulty a kontroly dedí z predlohy."""
