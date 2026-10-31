"""Metadáta WILLIAMS %R LONG 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'stopPct': 'Predloha nemá stop; engine potrebuje stop v pláne, preto poistka 10 %.',
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("wpr_entry", 'Vstup', ("wpr_entry",), "#26a69a"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "wpr_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
