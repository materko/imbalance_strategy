"""Druhy kresieb JSS — prerazená štruktúra (BOS / CHoCH), SD zóna a vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

JSS_BOS = DrawKind.register("jss_bos", "JSS_BOS")
JSS_CHOCH = DrawKind.register("jss_choch", "JSS_CHOCH")
JSS_ZONE = DrawKind.register("jss_zone", "JSS_ZONE")
JSS_REFINE = DrawKind.register("jss_refine", "JSS_REFINE")
JSS_ENTRY = DrawKind.register("jss_entry", "JSS_ENTRY")
