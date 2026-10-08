"""Metadáta Craig Percoco 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "htfTF": "Video číta smer a FVG na 15m a vstupuje na 1m — stratégia beží na 1m grafe a 15m si skladá sama.",
    "entryPct": "Vstup je vlastná limitka stratégie na stred FVG; spoločný typ vstupu (market / limit) sa na ňu nevzťahuje.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useHtfPoi"], "params": ["htfFvgMinAtr", "htfFvgMaxBars", "poiBars"]},
    {"switches": ["useTradeWindow"], "params": ["tradeTZ", "tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("htf", "15m FVG (body záujmu)", ("pc_htf_fvg",), "#a855f7"),
    ChartLayer("choch", "CHoCH", ("pc_choch",), "#10b981"),
    ChartLayer("fvg", "FVG vstupu", ("pc_fvg",), "#eab308"),
    ChartLayer("entries", "Vstupy", ("pc_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "pc_htf_fvg": "15m FVG",
    "pc_choch": "CHoCH",
    "pc_fvg": "FVG vstupu",
    "pc_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
