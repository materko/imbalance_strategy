"""Metadáta ASIA SWEEP 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "asiaStartH": "Klasický range Ázie (ICT) je 20:00–00:00 New York; celá ázijská seansa ~19:00–04:00.",
    "sweepStartH": "Londýnsky killzone 2:00–5:00 New York.",
    "useNpoc": "Naked POC = POC predošlého dňa, ktorý cena ešte nedotkla — cieľ, kam trh často smeruje.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["entryModel"], "when": {"entryModel": ["imbalance", "any"]}, "params": ["imbMinSize"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["pinbar", "any"]}, "params": ["pbWickPct", "pbBodyPct"]},
    {"switches": ["slMode"], "when": {"slMode": ["sweep", "signal"]}, "params": ["slBuffer"]},
    {"switches": ["slMode"], "when": {"slMode": ["atr"]}, "params": ["slAtr"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr", "npoc"]}, "params": ["rrRatio"]},
    {"switches": ["useExitTime"], "params": ["exitH", "exitM"]},
    {"switches": ["useNpoc"], "params": ["npocDays", "vpStartH", "vpStartM", "vpEndH", "vpEndM", "vpRowTicks", "showNpoc"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("range", "Range Ázie", ("as_range",), "#a855f7"),
    ChartLayer("sweeps", "Sweepy (vybratie likvidity)", ("as_sweep",), "#f59e0b"),
    ChartLayer("npoc", "Naked POC", ("as_npoc",), "#38bdf8"),
    ChartLayer("entries", "Vstupy", ("as_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "as_range": "Range Ázie",
    "as_sweep": "Sweep — prieraz maxima / minima Ázie",
    "as_npoc": "Naked POC (POC dňa, ktorý cena nedotkla)",
    "as_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
