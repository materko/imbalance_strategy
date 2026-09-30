"""Metadáta VWAP OP pre webapp — vrstvy grafu, závislosti prepínačov, poznámky k poliam."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "htf": "Predpokladá kalendárovo zarovnaný HTF (15m sedí s RTH otvorením 9:30 aj bez kotvy) — "
           "iná hodnota môže dať mierne iný grid než Pine na neštandardnom `rthSess`.",
    "driftAtr": "ATR je z HTF (15m), nie z grafu — na rozdiel od `tolAtr`/`slAtr`. Video/skript ich "
                "zámerne nemieša (drift meria pohyb VWAP, vstup a stop pohyb ceny na grafe).",
    "rr": "Skript stop ani cieľ neuvádza ako súčasť videa — RR 2 a SL 0,5 ATR sú východisko na test.",
    "useBE": "Jednorazový posun na breakeven, nie kontinuálny trailing — po +1R sa SL už nehýbe ďalej.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["showCross"], "params": ["colUp", "colDn", "colFlat"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("vwap", "VWAP (farba = drift)", ("vop_vwap",), "#10b981"),
    ChartLayer("entries", "Vstupy", ("vop_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "vop_vwap": "VWAP",
    "vop_entry": "Vstup (pullback k VWAP)",
    "tp_box": "TP box",
    "sl_box": "SL box",
}
