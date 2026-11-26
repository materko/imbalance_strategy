"""`MtkEmasBtcNetConfig` — tie isté parametre ako `mtkemasbtc`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..mtkemasbtc.config import MtkEmasBtcConfig

__all__ = ["MtkEmasBtcNetConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class MtkEmasBtcNetConfig(MtkEmasBtcConfig):
    """Config MTK EMAS 1.0 BTC (C# jadro) — polia, defaulty a kontroly dedí z predlohy."""
