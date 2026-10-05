"""Druhy kresieb FPC 1.0 — férová cena."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

FPC_WINDOW = DrawKind.register("fpc_window", "FPC_WINDOW")
FPC_FAIR = DrawKind.register("fpc_fair", "FPC_FAIR")
FPC_ZONE = DrawKind.register("fpc_zone", "FPC_ZONE")
FPC_NEWS = DrawKind.register("fpc_news", "FPC_NEWS")
FPC_VWAP = DrawKind.register("fpc_vwap", "FPC_VWAP")
FPC_SIGNAL = DrawKind.register("fpc_signal", "FPC_SIGNAL")
FPC_ENTRY = DrawKind.register("fpc_entry", "FPC_ENTRY")
