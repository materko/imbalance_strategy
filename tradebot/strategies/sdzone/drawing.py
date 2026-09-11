"""Druhy kresieb SD zón — box zóny, jej hranice, štítok formácie a vstupu."""

from __future__ import annotations

from tradebot.core.drawing import DrawKind

SD_DEMAND = DrawKind.register("sd_demand", "SD_DEMAND")
SD_SUPPLY = DrawKind.register("sd_supply", "SD_SUPPLY")
SD_BASE = DrawKind.register("sd_base", "SD_BASE")
SD_PATTERN = DrawKind.register("sd_pattern", "SD_PATTERN")
SD_ENTRY = DrawKind.register("sd_entry", "SD_ENTRY")
