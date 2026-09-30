"""Metadáta JSS pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "structTF": "TF štruktúry sa skladá z barov grafu; vstupné modely bežia na grafe — graf môže byť nižší TF "
                "(napr. štruktúra 5m, graf 2m).",
    "refineTF": "Pravidlo z 30. 9. 2026: BOS a zóna na 4h, v nej 15m zóna na upresnenie vstupu; limitka na 15m zónu.",
    "slBufferPoints": "Priestor za zónou v bodoch ceny, keby cena pred otočkou vybrala likviditu za zónou.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["structure"]}, "params": ["minRR"]},
    {"switches": ["zoneType"], "when": {"zoneType": ["base"]}, "params": ["baseMaxBars"]},
    {"switches": ["entryModel"], "when": {"entryModel": ["imbalance", "pinbar", "any"]},
     "params": ["confirmBars", "imbMinSizeAtr", "pbWickPct", "pbBodyPct"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("structure", "BOS / CHoCH", ("jss_bos", "jss_choch"), "#94a3b8"),
    ChartLayer("zones", "SD zóny", ("jss_zone", "jss_refine"), "#3b82f6"),
    ChartLayer("entries", "Vstupy", ("jss_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "jss_bos": "BOS",
    "jss_choch": "CHoCH",
    "jss_zone": "SD zóna (TF štruktúry)",
    "jss_refine": "Upresnená zóna (nižší TF)",
    "jss_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
