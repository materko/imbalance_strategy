"""Druhy kresieb LONDON LIQUIDITY IFVG 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

LLIQ_SESSION = DrawKind.register("lliq_session", "LLIQ_SESSION")
LLIQ_MARK = DrawKind.register("lliq_mark", "LLIQ_MARK")
LLIQ_ENTRY = DrawKind.register("lliq_entry", "LLIQ_ENTRY")
