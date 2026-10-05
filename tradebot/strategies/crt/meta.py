"""Metadáta CRT + TBS pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "rangeTF": "Sviečky vyššieho TF sa skladajú z barov grafu s hranicami podľa UTC (4h: 0, 4, 8, 12, 16, 20 h UTC).",
    "sweepKind": "body = turtle body soup (TBS): za hranicou rangu zavrie sviečka grafu; wick = stačí knôt.",
    "slBufferPoints": "Priestor za extrémom výberu v bodoch ceny.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["mid", "opposite"]}, "params": ["minRR"]},
    {"switches": ["requireOldHL"], "params": ["keyLookback"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["mss_fvg"]}, "params": ["swingLen", "fvgValidBars"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("ranges", "CRT range", ("crt_range", "crt_mid"), "#8b5cf6"),
    ChartLayer("sweeps", "Výber (turtle soup)", ("crt_sweep",), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("crt_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "crt_range": "CRT range (CRH – CRL)",
    "crt_mid": "Stred rangu (50 %)",
    "crt_sweep": "Výber hranice (turtle soup)",
    "crt_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
