"""Druhy kresieb Silver Bullet 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

SB_WINDOW = DrawKind.register("sb_window", "SB_WINDOW")
SB_LIQ_BUY = DrawKind.register("sb_liq_buy", "SB_LIQ_BUY")
SB_LIQ_SELL = DrawKind.register("sb_liq_sell", "SB_LIQ_SELL")
SB_SWEEP = DrawKind.register("sb_sweep", "SB_SWEEP")
SB_FVG = DrawKind.register("sb_fvg", "SB_FVG")
SB_ENTRY = DrawKind.register("sb_entry", "SB_ENTRY")
