"""Metadáta Silver Bullet 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "sbStartH": "ICT Silver Bullet: okno 10:00–11:00 New York; sweep, FVG aj vstup musia prísť v ňom.",
    "tpMode": "ICT: cieľ na protiľahlej likvidite (skorší vrchol pri longu, dno pri shorte).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useSwings"], "params": ["liqPivotLen"]},
    {"switches": ["requireMss"], "params": ["structPivotLen"]},
    {"switches": ["useExitTime"], "params": ["exitH", "exitM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["liquidity"]}, "params": ["minRR"]},
    {"switches": ["entryType"], "when": {"entryType": ["limit"]}, "params": ["entryLevel"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("window", "Okno 10–11 NY", ("sb_window",), "#a855f7"),
    ChartLayer("liquidity", "Likvidita a sweep", ("sb_liq_buy", "sb_liq_sell", "sb_sweep"), "#ef4444"),
    ChartLayer("fvg", "FVG", ("sb_fvg",), "#a855f7"),
    ChartLayer("entries", "Vstupy", ("sb_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "sb_window": "Okno Silver Bullet", "sb_liq_buy": "Buy-side likvidita (vrchol)",
    "sb_liq_sell": "Sell-side likvidita (dno)", "sb_sweep": "Sweep", "sb_fvg": "FVG vstupu", "sb_entry": "Vstup",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
