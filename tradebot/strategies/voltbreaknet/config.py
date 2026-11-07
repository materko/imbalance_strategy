"""`VoltBreakNetConfig` — tie isté parametre ako `voltbreak`; číta ich C# jadro (`tradebot/strategies/voltbreak/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..voltbreak.config import VoltBreakConfig

__all__ = ["VoltBreakNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class VoltBreakNetConfig(VoltBreakConfig):
    """Config Volt Break (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
