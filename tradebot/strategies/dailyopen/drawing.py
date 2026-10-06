"""Druhy kresieb DAILY OPEN."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

DO_LEVEL = DrawKind.register("do_level", "DO_LEVEL")
DO_BREAK = DrawKind.register("do_break", "DO_BREAK")
DO_ENTRY = DrawKind.register("do_entry", "DO_ENTRY")
