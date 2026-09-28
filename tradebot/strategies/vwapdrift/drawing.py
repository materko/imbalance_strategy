"""Druhy kresieb Drift VWAP — čiara VWAP (farbená driftom) a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

VD_VWAP = DrawKind.register("vd_vwap", "VD_VWAP")
VD_ENTRY = DrawKind.register("vd_entry", "VD_ENTRY")
