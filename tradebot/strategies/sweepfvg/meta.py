"""Metadáta SWEEP FVG 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "entryLevel": "Zadanie: vstup limitkou na okraji FVG; SL nad výber likvidity, TP nastaviteľné.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["startH", "startM", "endH", "endM"]},
    {"switches": ["useExitTime"], "params": ["exitH", "exitM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["points"]}, "params": ["tpPoints"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["liquidity"]}, "params": ["minRR"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("liquidity", "Likvidita", ("sf_liq_buy", "sf_liq_sell"), "#ef4444"),
    ChartLayer("structure", "Výber LQ a CHoCH / BOS", ("sf_sweep", "sf_struct"), "#6366f1"),
    ChartLayer("fvg", "FVG", ("sf_fvg",), "#a855f7"),
    ChartLayer("entries", "Vstupy", ("sf_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "sf_liq_buy": "Buy-side likvidita (BSL)", "sf_liq_sell": "Sell-side likvidita (SSL)",
    "sf_sweep": "Výber likvidity", "sf_struct": "CHoCH / BOS", "sf_fvg": "FVG vstupu", "sf_entry": "Vstup",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
