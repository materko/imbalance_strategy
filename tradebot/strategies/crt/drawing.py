"""Druhy kresieb CRT + TBS — range sviečky vyššieho TF, výber a vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

CRT_RANGE = DrawKind.register("crt_range", "CRT_RANGE")
CRT_MID = DrawKind.register("crt_mid", "CRT_MID")
CRT_SWEEP = DrawKind.register("crt_sweep", "CRT_SWEEP")
CRT_ENTRY = DrawKind.register("crt_entry", "CRT_ENTRY")
