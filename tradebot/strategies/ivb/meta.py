"""Metadáta IVB pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "riskDollar": "Predloha veľkosť počíta z 2 % účtu; engine stav účtu nepozná, preto riziko v $.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["flattenEod"], "params": ["eodFlatten"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "IB (9:30–10:00)", ("ivb_zone",), "#38bdf8"),
    ChartLayer("entries", "Vstupy", ("ivb_entry",), "#22c55e"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "ivb_zone": "IB",
    "ivb_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
