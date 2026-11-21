"""Metadáta IB RETRACE pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slRetr": "Video IB Lab: 70 % dní sa cena po prieraze nevráti hlbšie než long 0,60–0,69 / short 0,70–0,79 IB; "
              "presné čísla doplní štatistika.",
    "tpExt": "Video IB Lab: medián max extenzie +0,59 IB (najčastejšie okolo 12:00).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["closeAtEnd"], "params": ["exitTime"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Initial Balance", ("ibret_zone",), "#2196f3"),
    ChartLayer("entries", "Vstupy", ("ibret_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "ibret_zone": "Initial Balance",
    "ibret_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
