"""`MtkZoneNetConfig` — tie isté parametre ako MTK ZONE (`tradebot/strategies/mtkzone/config.py`); číta ich C# jadro
(`tradebot/strategies/mtkzone/ports/csharp/MtkZoneConfig.cs`). Vlastná trieda existuje len pre `spec_for_config`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkzone.config import MtkZoneConfig

__all__ = ["MtkZoneNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkZoneNetConfig(MtkZoneConfig):
    """Config MTK ZONE s jadrom v C# — polia, defaulty a kontroly dedí z predlohy."""
