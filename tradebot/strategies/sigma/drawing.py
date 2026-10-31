"""Druhy kresieb SIGMA BREAKOUT 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

SIGMA_BAND = DrawKind.register("sigma_band", "SIGMA_BAND")
SIGMA_ENTRY = DrawKind.register("sigma_entry", "SIGMA_ENTRY")
