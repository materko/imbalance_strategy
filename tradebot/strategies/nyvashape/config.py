"""`NyVaShapeConfig` — parametre NY VA BREAKOUT s podmienkou tvaru profilu P / b predvolene zapnutou."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..nyva.config import NyVaConfig

__all__ = ["NyVaShapeConfig", "CONFIG_DIR"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"


@dataclass
class NyVaShapeConfig(NyVaConfig):
    """Long nad VAH len pri P-profile prvej hodiny, short pod VAL len pri b-profile."""

    useShape: bool = True
