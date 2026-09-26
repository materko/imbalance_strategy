"""Popisy parametrov IBS FVG + IFVG — tie isté ako IBS Entry Zone, bez skupín S/R,
likvidity a Elliotta (tie polia formulár neukazuje, viď `meta.REMOVED_INPUTS`)."""

from ..ibsentry.params import GROUPS as _ENTRY_GROUPS
from ..ibsentry.params import PARAMS
from .meta import REMOVED_GROUPS

__all__ = ["GROUPS", "PARAMS"]

GROUPS: tuple[str, ...] = tuple(g for g in _ENTRY_GROUPS if g not in REMOVED_GROUPS)
