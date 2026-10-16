"""Metadáta NOA 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "hardStopPct": "Poistka mimo zdroja — výstup robia kontroly (VWAP / hranica) a 16:00.",
    "checkEvery": "Rozhoduje sa len na kontrolách; medzi nimi stratégia nič nerobí (zdroj).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("levels", "Hranice pásma", ("noa_level",), "#f59e0b"),
    ChartLayer("stop", "Úroveň výstupu", ("noa_stop",), "#f59e0b"),
    ChartLayer("vwap", "VWAP", ("noa_vwap",), "#a855f7"),
    ChartLayer("entries", "Vstupy", ("noa_entry",), "#10b981"),
    ChartLayer("tpsl", "Poistka a obchod", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "noa_level": "Hranica pásma", "noa_stop": "Úroveň výstupu", "noa_vwap": "VWAP", "noa_entry": "Vstup",
    "tp_box": "TP box", "sl_box": "Poistka (stop)", "entry": "Vstup", "exit": "Výstup",
}
