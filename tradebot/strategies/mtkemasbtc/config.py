"""`MtkEmasBtcConfig` — tie isté parametre ako `mtkemas` (vlastná trieda kvôli `spec_for_config`)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemas.config import MtkEmasConfig

__all__ = ["MtkEmasBtcConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasBtcConfig(MtkEmasConfig):
    """Config MTK EMAS 1.0 (BTC) — polia, defaulty a kontroly dedí z predlohy."""
