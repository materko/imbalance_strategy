"""`MtkEmasMgcNetConfig` — tie isté parametre ako `mtkemasmgc`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemasmgc.config import MtkEmasMgcConfig

__all__ = ["MtkEmasMgcNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasMgcNetConfig(MtkEmasMgcConfig):
    """Config MTK EMAS 1.0 MGC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
