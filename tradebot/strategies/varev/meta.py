"""Metadáta VALUE AREA REVERSION 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "profileSource": "Video (LuxAlgo): profil predošlého dňa dal čistejšie setupy ako rozvíjajúci sa dnešný.",
    "requireVolDecline": "Graf nemá bid / ask — medvedí objem = objem medvedej sviečky (rovnako ako LuxAlgo).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["startH", "startM", "endH", "endM"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("va", "Value area (VAH / VAL / POC)", ("vr_vah", "vr_val", "vr_poc"), "#089981"),
    ChartLayer("signals", "Únik a signály", ("vr_escape", "vr_signal"), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "vr_vah": "VAH", "vr_val": "VAL", "vr_poc": "POC", "vr_escape": "Únik z value area", "vr_signal": "Signál návratu",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
