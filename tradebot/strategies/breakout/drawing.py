"""Druhy kresieb Breakoutu — otváracia sviečka, jej hranice a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

BO_BOX = DrawKind.register("bo_box", "BO_BOX")
BO_HIGH = DrawKind.register("bo_high", "BO_HIGH")
BO_LOW = DrawKind.register("bo_low", "BO_LOW")
BO_ENTRY = DrawKind.register("bo_entry", "BO_ENTRY")
