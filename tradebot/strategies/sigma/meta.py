"""Metadáta SIGMA BREAKOUT 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'useCloseAtEnd': 'Predloha zatvára o 16:00 vždy — je to podstata stratégie (intraday).',
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("sigma_band", 'Pásmo', ("sigma_band",), "#ffd700"),
    ChartLayer("sigma_entry", 'Vstup', ("sigma_entry",), "#26a69a"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "sigma_band": 'Pásmo',
    "sigma_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
