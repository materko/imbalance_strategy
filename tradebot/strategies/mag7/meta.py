"""Metadáta Mag7 + SPX sila pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "waitMin": "Bežný pohyb sa meria v tej istej minúte ako sila — pri meraní po 10 min sa dnešný 10-minútový "
               "pohyb porovná s bežným 10-minútovým (Pine `refMin = waitMin`).",
    "s8": "S&P 500 je Dukascopy US500 (CFD na index); pohyb od 9:30 je ten istý ako pri SP:SPX.",
    "vwapData": "Pine počíta VWAP z 1m (výpočtový TF). Keď nástroj grafu nie je tento, VWAP sa skladá zo sviečok grafu.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useEma"], "params": ["emaLen"]},
    {"switches": ["useMag"], "params": ["magLen"]},
    {"switches": ["useOpen"], "params": ["minMove"]},
    {"switches": ["slMode"], "when": {"slMode": ["points"]}, "params": ["slPts"]},
    {"switches": ["slMode"], "when": {"slMode": ["open"]}, "params": ["slOpenBuf"]},
    {"switches": ["useEod"], "params": ["eodH", "eodM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("vwap", "VWAP od 9:30", ("m7_vwap",), "#f59e0b"),
    ChartLayer("mag", "Čiara MAG7", ("m7_line",), "#84cc16"),
    ChartLayer("ema", "EMA", ("m7_ema",), "#9333ea"),
    ChartLayer("open", "Open NY", ("m7_open",), "#a21caf"),
    ChartLayer("window", "Okno vstupu a meranie sily", ("m7_window", "m7_measure"), "#eab308"),
    ChartLayer("entries", "Vstupy", ("m7_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "m7_vwap": "VWAP Nasdaqu od 9:30 NY",
    "m7_line": "Čiara MAG7 (priemer Mag7 + SPX na cene Nasdaqu)",
    "m7_ema": "EMA na TF grafu",
    "m7_open": "Open NY",
    "m7_window": "Okno vstupu",
    "m7_measure": "Meranie sily (prvá sviečka po waitMin)",
    "m7_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
