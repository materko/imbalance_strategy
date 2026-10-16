"""Druhy kresieb NOA 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

NOA_LEVEL = DrawKind.register("noa_level", "NOA_LEVEL")
NOA_VWAP = DrawKind.register("noa_vwap", "NOA_VWAP")
NOA_STOP = DrawKind.register("noa_stop", "NOA_STOP")
NOA_ENTRY = DrawKind.register("noa_entry", "NOA_ENTRY")
