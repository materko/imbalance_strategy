"""Metadáta SWEEPING ENGULF 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "prevCandle": "Video (LuxAlgo): „Same direction is way better“ — predošlá sviečka smerom manipulácie.",
    "trendFilter": "Video: s EMA 200 menej trhané; profil mnq_databento_4h ho má zapnutý (with, 200).",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["slMethod"], "when": {"slMethod": ["atr"]}, "params": ["atrMult"]},
    {"switches": ["slMethod"], "when": {"slMethod": ["candle"]}, "params": ["slBufferAtr"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("signals", "Signály", ("se_signal",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "se_signal": "Signál (výber + pohltenie)", "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
