"""Druhy kresieb Fibo — noha, úrovne a vstupy."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

FIB_LEG = DrawKind.register("fib_leg", "FIB_LEG")
FIB_LEVEL = DrawKind.register("fib_level", "FIB_LEVEL")
FIB_ENTRY = DrawKind.register("fib_entry", "FIB_ENTRY")
