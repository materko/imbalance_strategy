"""`Va80NetConfig` — tie isté parametre ako `va80`; číta ich C# jadro (`tradebot/strategies/va80/ports/csharp`).

Vlastná trieda existuje len preto, že registry hľadá stratégiu podľa triedy configu (`spec_for_config`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..va80.config import Va80Config

__all__ = ["Va80NetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class Va80NetConfig(Va80Config):
    """Config VA NÁVRAT 1.0 (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
