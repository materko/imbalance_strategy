"""Metadáta Volt Break pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "tpUsd": "TP/SL sa merajú od zavretia signálnej sviečky; Pine ich meria od skutočnej ceny vstupu "
             "(otvorenie ďalšej sviečky) — rozdiel je medzera medzi nimi.",
    "usdPerPoint": "Doslovný Pine na grafe MNQ by z 800 $ urobil 400 bodov; tu sa drží zámer skriptu (NQ).",
}

FEATURES: list[dict[str, Any]] = []

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("noise", "Noise Up", ("vb_noise",), "#f59e0b"),
    ChartLayer("vwap", "VWAP", ("vb_vwap",), "#3b82f6"),
    ChartLayer("entries", "Vstupy", ("vb_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "vb_noise": "Noise Up", "vb_vwap": "VWAP", "vb_entry": "Vstup", "tp_box": "TP box", "sl_box": "SL box",
}
