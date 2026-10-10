"""Druhy kresieb SWEEP FVG 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

SF_LIQ_BUY = DrawKind.register("sf_liq_buy", "SF_LIQ_BUY")
SF_LIQ_SELL = DrawKind.register("sf_liq_sell", "SF_LIQ_SELL")
SF_SWEEP = DrawKind.register("sf_sweep", "SF_SWEEP")
SF_STRUCT = DrawKind.register("sf_struct", "SF_STRUCT")
SF_FVG = DrawKind.register("sf_fvg", "SF_FVG")
SF_ENTRY = DrawKind.register("sf_entry", "SF_ENTRY")
