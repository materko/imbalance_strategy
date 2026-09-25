"""`IBSEntryZoneConfig` — parametre IBS plus štvrtý zdroj zón (veľké imbalance).

Prepínače sú zámerne postavené ako `enableSrTrading` a `enableLqTrading` v IBS: jeden
hlavný, ktorý zdroj zapína, a k nemu to, z čoho sa zóny berú. Zóna z FVG sa potom
obchoduje rovnakým modelom ako každá iná, takže vlastné entry parametre nepotrebuje.

Platnosť zóny sa berie zo spoločného `zoneValidHours` — rovnako ako pri zónach zo S/R
a z likvidity, ktoré ju tiež nemajú vlastnú.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from tradebot.core.types import SizeSpec, SizeUnit

from ..ibs.config import CONSTRAINTS as IBS_CONSTRAINTS
from ..ibs.config import ENUM_FIELDS as IBS_ENUM_FIELDS
from ..ibs.config import SIZE_FIELDS as IBS_SIZE_FIELDS
from ..ibs.config import IBSConfig

__all__ = ["IBSEntryZoneConfig", "CONFIG_DIR", "CONSTRAINTS", "ENUM_FIELDS", "SIZE_FIELDS"]

CONFIG_DIR = Path(__file__).resolve().parent / "configs"

SIZE_FIELDS: dict[str, SizeUnit] = {**IBS_SIZE_FIELDS, "fvgMinSize": "abs"}
ENUM_FIELDS: dict[str, type] = dict(IBS_ENUM_FIELDS)
CONSTRAINTS: dict[str, tuple[float, float]] = {**IBS_CONSTRAINTS, "fvgMinSize": (0, 500)}


def _size(value: float, name: str) -> SizeSpec:
    return SizeSpec(value, SIZE_FIELDS[name])


@dataclass
class IBSEntryZoneConfig(IBSConfig):
    """Config IBS Entry Zone — IBS plus zóny z veľkých imbalance."""

    SIZE_FIELDS: ClassVar[dict[str, SizeUnit]] = SIZE_FIELDS
    ENUM_FIELDS: ClassVar[dict[str, type]] = ENUM_FIELDS
    CONSTRAINTS: ClassVar[dict[str, tuple[float, float]]] = CONSTRAINTS

    # ---- 💠 Zóny z imbalance (FVG) --------------------------------------- #
    enableFvgTrading: bool = True
    fvgUse5m: bool = True
    fvgUse15m: bool = True
    fvgUse30m: bool = True
    fvgUse60m: bool = True
    fvgMinSize: SizeSpec = field(default_factory=lambda: _size(5.0, "fvgMinSize"))

    def _problems(self) -> Iterable[str]:
        yield from super()._problems()
        if self.enableFvgTrading and not self.active_fvg_timeframes():
            yield (
                "enableFvgTrading je zapnuté, ale nie je zvolený ani jeden TF "
                "(fvgUse5m, fvgUse15m, fvgUse30m, fvgUse60m) — zóny by nemali z čoho vznikať"
            )

    def active_fvg_timeframes(self) -> tuple[int, ...]:
        """Minúty TF, z ktorých sa veľké imbalance naozaj čítajú."""
        from .fvg import FVG_TIMEFRAMES

        return tuple(minutes for fieldname, minutes in FVG_TIMEFRAMES if getattr(self, fieldname))
