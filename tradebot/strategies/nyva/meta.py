"""Metadáta NY VA BREAKOUT pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "profileRows": "Profil je zo sviečok grafu — na 1–3m presnejší, na 5m+ hrubší.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useCloseTime"], "params": ["closeH", "closeM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("range", "Range prvej hodiny", ("nv_range",), "#94a3b8"),
    ChartLayer("levels", "POC / VAH / VAL", ("nv_poc", "nv_va"), "#facc15"),
    ChartLayer("entries", "Vstupy", ("nv_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "nv_range": "Range prvej hodiny",
    "nv_poc": "POC",
    "nv_va": "VAH / VAL",
    "nv_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
