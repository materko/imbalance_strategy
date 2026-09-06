"""Metadáta ukážkovej stratégie pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()
PARAM_NOTES: dict[str, str] = {}

PORT_ONLY_META: dict[str, dict[str, Any]] = {
    "leverage": dict(
        title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based sizingu, "
        "ktorá by sa inak na účet nezmestila.",
    ),
}

#: Závislosti prepínač -> podnastavenia (ukážka: showChannel nemá podnastavenia, allowShort tiež).
FEATURES: list[dict[str, Any]] = []

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("channel", "Donchian kanál", ("dc_upper", "dc_lower"), "#3b82f6"),
    ChartLayer("entries", "Vstupy", ("demo_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "dc_upper": "Kanál hore", "dc_lower": "Kanál dole", "demo_entry": "Vstup (breakout)",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
