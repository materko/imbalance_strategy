"""Druhy kresieb VWAP ADX — VWAP, opening range a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

VA_VWAP = DrawKind.register("va_vwap", "VA_VWAP")
VA_RANGE = DrawKind.register("va_range", "VA_RANGE")
VA_ENTRY = DrawKind.register("va_entry", "VA_ENTRY")
