"""Metadáta SD ZÓNY EURUSD pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "zoneTF": "Graf 5m, zóny na 1 h — zónu nehľadaj na grafe 1m (limity sú v sviečkach).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useFormWindow"], "params": ["formStartH", "formEndH"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Supply / demand zóny", ("se_supply", "se_demand"), "#ef4444"),
    ChartLayer("entries", "Vstupy", ("se_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "se_supply": "Supply zóna",
    "se_demand": "Demand zóna",
    "se_entry": "Vstup",
    "tp_box": "Cieľ",
    "sl_box": "Stop",
    "entry": "Vstup",
    "exit": "Výstup",
}
