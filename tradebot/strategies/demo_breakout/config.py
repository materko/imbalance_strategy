"""Config ukážkovej stratégie Demo Donchian Breakout — 8 vstupov z `pine/demo_breakout.pine`.

Názvy polí sú zhodné s Pine identifikátormi, rovnako ako pri IBS. `leverage` je
rozšírenie portu (Freqtrade futures), Pine ho nemá.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Iterable

from tradebot.core.config import CONFIGS_ROOT, StrategyConfig
from tradebot.core.types import SizeSpec, SizeUnit

__all__ = ["DemoBreakoutConfig", "ExitMode", "CONFIG_DIR"]

CONFIG_DIR = CONFIGS_ROOT / "demo_breakout"


class ExitMode(str, Enum):
    """Pine `exitMode`."""

    OPPOSITE = "opposite"
    TP_ONLY = "tp_only"


SIZE_FIELDS: dict[str, SizeUnit] = {"slAtrMult": "atr"}

ENUM_FIELDS: dict[str, type] = {"exitMode": ExitMode}

CONSTRAINTS: dict[str, tuple[float, float]] = {
    "channelLen": (5, 200),
    "atrLen": (2, 100),
    "slAtrMult": (0.1, 10),
    "rrRatio": (0.5, 10),
    "riskDollar": (0, 100000),
    "leverage": (1, 125),
}

PORT_ONLY_FIELDS: frozenset[str] = frozenset({"leverage"})


@dataclass
class DemoBreakoutConfig(StrategyConfig):
    """Defaulty = Pine defaulty."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS
    PORT_ONLY_FIELDS: ClassVar[frozenset[str]] = PORT_ONLY_FIELDS

    # ---- 🎯 Obchodovanie ------------------------------------------------ #
    channelLen: int = 20
    atrLen: int = 14
    slAtrMult: SizeSpec = field(default_factory=lambda: SizeSpec(1.5, "atr"))
    rrRatio: float = 2.0
    allowShort: bool = True
    exitMode: ExitMode = ExitMode.OPPOSITE
    # ---- 💰 Riziko -------------------------------------------------------- #
    riskDollar: float = 100.0
    # ---- 🎨 Vizualizacia -------------------------------------------------- #
    showChannel: bool = True
    # ---- rozšírenia portu ------------------------------------------------- #
    #: Páka vo Freqtrade futures — Pine ju nemá.
    leverage: float = 1.0

    def _problems(self) -> Iterable[str]:
        if self.leverage < 1:
            yield f"leverage={self.leverage} musí byť >= 1"
