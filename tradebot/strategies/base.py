"""Popis stratégie pre registry — čo o nej potrebujú adaptéry, webapp a testy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.config import StrategyConfig


@dataclass(frozen=True)
class StrategySpec:
    """Jedna stratégia v registry. Rozširuje sa po fázach (engine, adaptéry, metadáta)."""

    key: str
    title: str
    config_cls: type[StrategyConfig]
    profile_dir: Path
    default_profile: str
