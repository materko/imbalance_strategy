"""`MtkEmasEsNetConfig` — tie isté parametre ako `mtkemases`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemases.config import MtkEmasEsConfig

__all__ = ["MtkEmasEsNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasEsNetConfig(MtkEmasEsConfig):
    """Config MTK EMAS 1.0 ES (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
