"""Metadáta VWAP ADX pre webapp — vrstvy grafu a poznámky k poliam."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "tpBars": "Stratégia je písaná na 1m graf — počty barov (TP, SL, ADX) znamenajú na inom TF inú stratégiu.",
    "slBars": "Signál so stopom presne na zavretí (low posledných N = close) sa preskočí — nemá vzdialenosť stopu.",
    "exitHHMM": "Časový exit je z videa; pozícia sa nikdy nedrží cez noc, lebo signály končia pred ním.",
}

FEATURES: list[dict[str, Any]] = []

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("vwap", "VWAP", ("va_vwap",), "#3b82f6"),
    ChartLayer("range", "Opening range", ("va_range",), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("va_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "va_vwap": "VWAP",
    "va_range": "Opening range",
    "va_entry": "Vstup (pullback k VWAP)",
    "tp_box": "TP box",
    "sl_box": "SL box",
}
