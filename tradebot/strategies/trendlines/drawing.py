"""Druhy kresieb Trendline Breakout — trendovky, pivoty, prerazenia a vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

TL_RESISTANCE = DrawKind.register("tl_resistance", "TL_RESISTANCE")
TL_SUPPORT = DrawKind.register("tl_support", "TL_SUPPORT")
TL_PIVOT = DrawKind.register("tl_pivot", "TL_PIVOT")
TL_BREAK = DrawKind.register("tl_break", "TL_BREAK")
TL_ENTRY = DrawKind.register("tl_entry", "TL_ENTRY")
