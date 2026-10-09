"""Druhy kresieb Overnight Bias ORB — overnight range s tretinami, opening range, vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

OB_OVERNIGHT = DrawKind.register("ob_overnight", "OB_OVERNIGHT")
OB_THIRDS = DrawKind.register("ob_thirds", "OB_THIRDS")
OB_RANGE = DrawKind.register("ob_range", "OB_RANGE")
OB_ENTRY = DrawKind.register("ob_entry", "OB_ENTRY")
