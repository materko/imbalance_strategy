"""Metadáta DAILY OPEN pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slPts": "Video: stop 1 000 $ na NQ = 50 bodov (MNQ: 100 $). Variant: 800 $ = 40 bodov.",
    "breakPts": "Video: 30 bodov; autor skúšal 10–40, výsledky podobné.",
    "exitH": "Video: koniec dennej seansy 16:00 NY; variant 14:00.",
    "breakMode": "Video: „po polnoci cena nad zavretím = deň sa dá obchodovať“ — či to musí byť už v noci, nepovedal.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["fixedQty"], "params": ["qty"]},
    {"switches": ["useExit"], "params": ["exitH", "exitM"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("level", "Zavretie polnoci a úroveň prierazu", ("do_level", "do_break"), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("do_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "do_level": "Zavretie polnoci NY (úroveň)",
    "do_break": "Úroveň prierazu (zavretie ± prah)",
    "do_entry": "Vstup",
    "tp_box": "TP box (bez cieľa: 1R na orientáciu)",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
