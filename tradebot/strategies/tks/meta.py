"""Metadáta TKS 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()
PARAM_NOTES: dict[str, str] = {"loLevel": "Zadanie: 35 / 65 (čiary indikátora NQ Kompas); test: 20 / 80 lepšie."}
FEATURES: list[dict[str, Any]] = [{"switches": ["fixedQty"], "params": ["qty"]}]
LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("entries", "Vstupy", ("tks_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)
KIND_TITLES: dict[str, str] = {"tks_entry": "Vstup", "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup"}
