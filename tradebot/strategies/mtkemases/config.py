"""`MtkEmasEsConfig` — tie isté parametre ako `mtkemas` (vlastná trieda kvôli `spec_for_config`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemas.config import MtkEmasConfig

__all__ = ["MtkEmasEsConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasEsConfig(MtkEmasConfig):
    """Config MTK EMAS 1.0 (ES) — polia, defaulty a kontroly dedí z predlohy."""
