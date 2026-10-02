"""Metadáta Volume Profile POC pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "rowTicks": "Profil sa počíta z barov grafu: objem baru sa rozloží rovnomerne medzi jeho low a high. "
                "Jemnejší graf (2m, 3m) dáva presnejší profil.",
    "pocSource": "previous = POC včerajšej seansy, pevná úroveň; developing = POC dnešnej seansy, hýbe sa.",
    "tradeMode": "rejection = pod POC short, nad POC long na dotyk; retest = len po prerazení POC zavretím.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM", "closeAtWindowEnd"]},
    {"switches": ["slMode"], "when": {"slMode": ["atr"]}, "params": ["slAtr"]},
    {"switches": ["slMode"], "when": {"slMode": ["points"]}, "params": ["slPoints"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["va_edge"]}, "params": ["minRR"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["imbalance", "pinbar", "any"]},
     "params": ["confirmBars", "touchTolAtr", "imbMinSizeAtr", "pbWickPct", "pbBodyPct"]},
    {"switches": ["tradeMode"], "when": {"tradeMode": ["retest", "rejection"]}, "params": ["retestMaxBars", "breakBufferAtr"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("poc", "POC", ("svp_poc",), "#f59e0b"),
    ChartLayer("va", "Value area (VAH / VAL)", ("svp_va",), "#64748b"),
    ChartLayer("entries", "Vstupy", ("svp_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "svp_poc": "POC (point of control)",
    "svp_va": "Hrana value area",
    "svp_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
