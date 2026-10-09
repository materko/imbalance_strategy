"""Metadáta Overnight Bias ORB pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slPct": "SL/TP sa merajú od zavretia signálnej sviečky; Pine ich meria od ceny vstupu (open ďalšej sviečky).",
    "avgLen": "Kým nie je dosť seáns na priemer ATR, signál sa preskočí (Pine by vstúpil bez stopu).",
    "rthHHMM": "Opening range je jedna sviečka od tohto času — skript je písaný na 15m graf.",
}

FEATURES: list[dict[str, Any]] = []

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("overnight", "Overnight range a tretiny", ("ob_overnight", "ob_thirds"), "#14b8a6"),
    ChartLayer("range", "Opening range (farba = bias)", ("ob_range",), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("ob_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "ob_overnight": "Overnight range", "ob_thirds": "Tretiny overnight rangu", "ob_range": "Opening range",
    "ob_entry": "Vstup", "tp_box": "TP box", "sl_box": "SL box",
}
