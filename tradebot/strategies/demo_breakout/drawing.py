"""Druhy kresieb ukážkovej stratégie — hrany Donchian kanála a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

DC_UPPER = DrawKind.register("dc_upper", "DC_UPPER")
DC_LOWER = DrawKind.register("dc_lower", "DC_LOWER")
DEMO_ENTRY = DrawKind.register("demo_entry", "DEMO_ENTRY")
