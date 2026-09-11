"""Druhy kresieb range breakoutu — box konsolidácie, jej hranice, štítky vstupu a retestu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

RANGE_BOX = DrawKind.register("range_box", "RANGE_BOX")
RANGE_HIGH = DrawKind.register("range_high", "RANGE_HIGH")
RANGE_LOW = DrawKind.register("range_low", "RANGE_LOW")
RANGE_BREAK = DrawKind.register("range_break", "RANGE_BREAK")
RANGE_ENTRY = DrawKind.register("range_entry", "RANGE_ENTRY")
