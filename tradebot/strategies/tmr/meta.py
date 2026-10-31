"""Metadáta T-MEAN REVERSION 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'stopPct': 'Predloha nemá stop ani cieľ; engine potrebuje stop v pláne, preto poistka 10 %.',
}

FEATURES: list[dict[str, Any]] = [
    {'switches': ['checkMarketHours'], 'params': ['marketOpenHour', 'marketCloseHour']},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("tmr_entry", 'Vstup', ("tmr_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "tmr_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
