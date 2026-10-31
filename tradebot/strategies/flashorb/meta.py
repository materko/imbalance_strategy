"""Metadáta FLASH TRIGGER ORB 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    'useEodClose': 'Predloha zatvára vždy (23:59 UTC); prepínač je rozšírenie portu kvôli smernici.',
}

FEATURES: list[dict[str, Any]] = [
    {'switches': ['dayFilter'], 'params': ['tradeMonday', 'tradeTuesday', 'tradeWednesday', 'tradeThursday', 'tradeFriday']},
    {'switches': ['activateTrailing'], 'params': ['trailActivatePoints', 'trailBufferPoints']},
    {'switches': ['useEodClose'], 'params': ['eodHour', 'eodMinute']},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("flashorb_zone", 'Vybraná sviečka', ("flashorb_zone",), "#00c853"),
    ChartLayer("flashorb_entry", 'Vstup', ("flashorb_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "flashorb_zone": 'Vybraná sviečka',
    "flashorb_entry": 'Vstup',
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
