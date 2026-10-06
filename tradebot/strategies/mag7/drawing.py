"""Druhy kresieb Mag7 + SPX sila."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

M7_VWAP = DrawKind.register("m7_vwap", "M7_VWAP")
M7_LINE = DrawKind.register("m7_line", "M7_LINE")
M7_EMA = DrawKind.register("m7_ema", "M7_EMA")
M7_OPEN = DrawKind.register("m7_open", "M7_OPEN")
M7_WINDOW = DrawKind.register("m7_window", "M7_WINDOW")
M7_MEASURE = DrawKind.register("m7_measure", "M7_MEASURE")
M7_ENTRY = DrawKind.register("m7_entry", "M7_ENTRY")
