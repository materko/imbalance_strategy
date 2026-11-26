"""`MtkEmasNetConfig` — tie isté parametre ako MTK EMAS 1.0 (`tradebot/strategies/mtkemas/config.py`).

Parametre, rozsahy aj profily sú zámerne zhodné s predlohou, aby sa behy dali porovnať jedna k jednej;
číta ich C# jadro (`tradebot/strategies/mtkemas/ports/csharp/MtkEmasConfig.cs`). Vlastná trieda existuje len
preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemas.config import MtkEmasConfig

__all__ = ["MtkEmasNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasNetConfig(MtkEmasConfig):
    """Config MTK EMAS 1.0 s jadrom v C# — polia, defaulty a kontroly dedí z predlohy."""
