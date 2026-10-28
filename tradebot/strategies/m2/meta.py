"""Metadáta M2 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "ema5": "Podklad je na ES 1m — EMA 1200 je ~20 hodín; na vyššom TF sa dĺžky v sviečkach nepresúvajú samy.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useEmaTrend"], "params": ["ema1", "ema2", "ema3", "ema4", "ema5", "emaNeedClose"]},
    {"switches": ["useWindow"], "params": ["entryStartH", "entryStartM", "entryEndH", "entryEndM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "M2 (posledná opačná sviečka)", ("m2_zone",), "#3b82f6"),
    ChartLayer("entries", "Vstupy", ("m2_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "m2_zone": "M2",
    "m2_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
