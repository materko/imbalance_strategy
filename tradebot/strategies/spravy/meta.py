"""Metadáta SPRÁVY pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "trendEvents": "Čas správ je New York (kalendár v balíku). Na Slovensku je to bežne +6 h, v týždňoch posunu času +5 h.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("legs", "Noha po správe", ("sp_leg",), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("sp_entry",), "#10b981"),
    ChartLayer("tpsl", "SL", ("sl_box", "tp_box", "entry", "exit"), "#ef4444"),
)

KIND_TITLES: dict[str, str] = {
    "sp_leg": "Noha po správe",
    "sp_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
