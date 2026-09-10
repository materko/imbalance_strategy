"""Druhy kresieb Gap Fill — box medzery, cieľová úroveň výplne a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

GAP_BOX = DrawKind.register("gap_box", "GAP_BOX")
GAP_TARGET = DrawKind.register("gap_target", "GAP_TARGET")
GAP_ENTRY = DrawKind.register("gap_entry", "GAP_ENTRY")
