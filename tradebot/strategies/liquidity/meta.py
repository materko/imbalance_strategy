"""Metadáta Liquidity pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "tradeMode": "Meranie na MNQ (2019-2026): po vybratí likvidity sa cena nevracia častejšie ako pri "
                 "náhodnej úrovni, ale pohyb je väčší oboma smermi — o niečo viac v smere pokračovania.",
    "liqMinDispAtr": "Výrazný swing = cena z neho odišla aspoň o toľko ATR; to sú body, z ktorých sa "
                     "likvidita značí ručne.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useTradeWindow"], "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["liquidity"]}, "params": ["minRR", "maxRR", "tpOffsetAtr"]},
    {"switches": ["tpMode"], "when": {"tpMode": ["rr"]}, "params": ["rrRatio"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("liquidity", "Likvidita", ("liq_buy", "liq_sell"), "#ef4444"),
    ChartLayer("events", "Sweepy a prerazenia", ("liq_event",), "#6366f1"),
    ChartLayer("entries", "Vstupy", ("liq_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "liq_buy": "Buy-side likvidita (BSL)",
    "liq_sell": "Sell-side likvidita (SSL)",
    "liq_event": "Sweep / prerazenie",
    "liq_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
