"""Druhy kresieb Volt Break — Noise Up, VWAP a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

VB_NOISE = DrawKind.register("vb_noise", "VB_NOISE")
VB_VWAP = DrawKind.register("vb_vwap", "VB_VWAP")
VB_ENTRY = DrawKind.register("vb_entry", "VB_ENTRY")
