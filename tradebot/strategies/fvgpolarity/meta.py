"""Metadáta FVG POLARITY pre webapp — vrstvy grafu a poznámky k poliam."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "slPoints": "Body ceny, nie ATR — tak bolo zadanie pre MNQ; na inom trhu treba prepočítať.",
    "tpLevel": "Cieľ je v smere k medzere: po medvedom FVG long hore k jej spodnej hrane, po býčom short "
               "dole k jej hornej hrane.",
}

FEATURES: list[dict[str, Any]] = [{"switches": ["showFvg"], "params": []}]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("fvg", "FVG", ("fp_fvg",), "#be185d"),
    ChartLayer("entries", "Vstupy", ("fp_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "fp_fvg": "FVG",
    "fp_entry": "Vstup (k FVG)",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
