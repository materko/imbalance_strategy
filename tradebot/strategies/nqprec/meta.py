"""Metadáta NQ PRECISION 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'triggerTime': 'Predloha 9:59:55 na tickoch; na 1m sviečkach zavretie baru 9:59.',
}

FEATURES: list[dict[str, Any]] = [
    {'switches': ['useFilters'], 'params': ['rvolLen', 'rvolMin', 'rvolMax', 'atrRegimeLen', 'regimeMin', 'regimeMax']},
    {'switches': ['useTimeClose'], 'params': ['closeAfterMin']},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("nqprec_zone", 'Opening range', ("nqprec_zone",), "#00c853"),
    ChartLayer("nqprec_entry", 'Vstup', ("nqprec_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "nqprec_zone": 'Opening range',
    "nqprec_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
