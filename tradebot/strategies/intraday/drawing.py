"""Druhy kresieb INTRADAY 1.0."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

ID_ZONE = DrawKind.register("id_zone", "ID_ZONE")
ID_LIQ = DrawKind.register("id_liq", "ID_LIQ")
ID_SWEEP = DrawKind.register("id_sweep", "ID_SWEEP")
ID_ENTRY = DrawKind.register("id_entry", "ID_ENTRY")
