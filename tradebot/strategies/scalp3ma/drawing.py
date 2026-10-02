"""Druhy kresieb Scalping 3MA + RSI + fraktál."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

S3_MA = DrawKind.register("s3_ma", "S3_MA")
S3_FRACTAL = DrawKind.register("s3_fractal", "S3_FRACTAL")
S3_ENTRY = DrawKind.register("s3_entry", "S3_ENTRY")
