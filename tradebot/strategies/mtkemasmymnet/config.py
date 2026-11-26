"""`MtkEmasMymNetConfig` — tie isté parametre ako `mtkemasmym`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemasmym.config import MtkEmasMymConfig

__all__ = ["MtkEmasMymNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasMymNetConfig(MtkEmasMymConfig):
    """Config MTK EMAS 1.0 MYM (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
