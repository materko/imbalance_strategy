"""Druhy kresieb VWAP OP — čiara VWAP (farbená driftom) a štítok vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

VOP_VWAP = DrawKind.register("vop_vwap", "VOP_VWAP")
VOP_ENTRY = DrawKind.register("vop_entry", "VOP_ENTRY")
