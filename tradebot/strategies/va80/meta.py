"""Metadáta VA NÁVRAT 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'exitTime': 'Výstup v čase je podstata stratégie (návrat do VA počas dňa), nie koniec seansy na zatvorenie.',
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("va80_level", 'Value area', ("va80_level",), "#5b9cf6"),
    ChartLayer("va80_entry", 'Vstup', ("va80_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "va80_level": 'Value area',
    "va80_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
