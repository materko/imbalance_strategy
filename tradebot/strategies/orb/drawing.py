"""Druhy kresieb ORB — box opening rangu, jeho hranice a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

ORB_BOX = DrawKind.register("orb_box", "ORB_BOX")
ORB_HIGH = DrawKind.register("orb_high", "ORB_HIGH")
ORB_LOW = DrawKind.register("orb_low", "ORB_LOW")
ORB_ENTRY = DrawKind.register("orb_entry", "ORB_ENTRY")
