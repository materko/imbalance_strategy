"""`MtkOrbNetConfig` — tie isté parametre ako `mtkorb`; číta ich C# jadro (`tradebot/strategies/orb15/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkorb.config import MtkOrbConfig

__all__ = ["MtkOrbNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkOrbNetConfig(MtkOrbConfig):
    """Config MTK ORB MGC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
