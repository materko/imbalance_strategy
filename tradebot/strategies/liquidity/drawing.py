"""Druhy kresieb Liquidity — úrovne likvidity, udalosti (sweep, prerazenie) a vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

LIQ_BUY = DrawKind.register("liq_buy", "LIQ_BUY")
LIQ_SELL = DrawKind.register("liq_sell", "LIQ_SELL")
LIQ_EVENT = DrawKind.register("liq_event", "LIQ_EVENT")
LIQ_ENTRY = DrawKind.register("liq_entry", "LIQ_ENTRY")
