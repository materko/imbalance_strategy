"""Metadáta Fibo pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "swingTF": "Swingy sa hľadajú na tomto TF (skladá sa z barov grafu); vstupné modely bežia na grafe — graf môže byť nižší TF.",
    "tpExtensionPct": "Video: cieľ na extenzii −27 % (27), ďalšia je −61,8 % (61.8); 0 = koniec nohy.",
    "slMode": "Video dáva stop za swing. leg = začiatok nohy (100 %), pullback = extrém návratu (tesnejší).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["extension"]}, "params": ["tpExtensionPct", "minRR"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["pinbar", "any"]}, "params": ["pbWickPct", "pbBodyPct"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["imbalance", "any"]}, "params": ["imbMinSizeAtr"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("fibo", "Fibonacci (noha a úrovne)", ("fib_leg", "fib_level"), "#eab308"),
    ChartLayer("entries", "Vstupy", ("fib_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "fib_leg": "Noha (impulz)",
    "fib_level": "Fibonacciho úroveň",
    "fib_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
