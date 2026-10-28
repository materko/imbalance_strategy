"""Metadáta NB pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "consBars": "Graf M15, trend H4 — na grafe 1m by konsolidácia z 8 sviečok bola 8 minút (limity sú v sviečkach).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useHtfTrend"], "params": ["htfTF", "htfNeedClose"]},
    {"switches": ["useRoom"], "params": ["roomMinR", "pivotLen"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Konsolidácie", ("nb_zone",), "#8b5cf6"),
    ChartLayer("entries", "Vstupy", ("nb_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "nb_zone": "Konsolidácia",
    "nb_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
