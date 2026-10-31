"""Metadáta LONDON LIQUIDITY IFVG 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
}

FEATURES: list[dict[str, Any]] = [
    {'switches': ['useDayFilter'], 'params': ['tradeMon', 'tradeTue', 'tradeWed', 'tradeThu', 'tradeFri']},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("lliq_session", 'Seansa', ("lliq_session",), "#808080"),
    ChartLayer("lliq_mark", 'LS / IFVG', ("lliq_mark",), "#ff0000"),
    ChartLayer("lliq_entry", 'Vstup', ("lliq_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "lliq_session": 'Seansa',
    "lliq_mark": 'LS / IFVG',
    "lliq_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
