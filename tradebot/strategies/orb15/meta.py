"""Metadáta ORB 15/5 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "allowLong": "Predloha má long aj short predvolene vypnuté (bez obchodov); tu zapnuté.",
    "riskDollar": "Predloha: 500 $ riziko na obchod (size_mode 0).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useWickFilter"], "params": ["maxWickPct"]},
    {"switches": ["useDailyBias"], "params": ["biasCheck"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Opening range", ("orb15_zone",), "#2196f3"),
    ChartLayer("entries", "Vstupy", ("orb15_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "orb15_zone": "Opening range",
    "orb15_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
