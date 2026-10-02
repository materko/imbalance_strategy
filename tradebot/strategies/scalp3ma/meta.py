"""Metadáta Scalping 3MA + RSI + fraktál pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slPoints": "Video: stop 5 pipov na EURUSD = 0,0005; cieľ 10 pipov = RR 2.",
    "maxTradesPerDay": "Video odporúča jeden obchod denne — podmienky vznikajú často a ľahko sa preobchoduje.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
    {"switches": ["slMode"], "when": {"slMode": ["points"]}, "params": ["slPoints"]},
    {"switches": ["slMode"], "when": {"slMode": ["atr"]}, "params": ["slAtr"]},
    {"switches": ["slMode"], "when": {"slMode": ["fractal"]}, "params": ["slBufferAtr"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("ma", "SMMA 20 / 60 / 200", ("s3_ma",), "#3b82f6"),
    ChartLayer("fractals", "Fraktály (signál)", ("s3_fractal",), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("s3_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "s3_ma": "Vyhladený priemer (SMMA)",
    "s3_fractal": "Fraktál, ktorý dal signál",
    "s3_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
