"""Metadáta MTK EMAS pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "tradeDirection": "Štúdia Mac mini (25. 11. 2026): shorty majú PF pod 1 takmer na všetkých trhoch — len longy.",
    "signalMode": "Štúdia: cena × dlhý priemer (80–200) často lepšia než kríženie dvoch priemerov.",
    "trailAtr": "Štúdia: indexy 2–4 ATR (+ zámok pri 1R), zlato a BTC 4–6 ATR.",
}

FEATURES: list[dict[str, Any]] = [{"switches": ["fixedQty"], "params": ["qty"]}]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("entries", "Vstupy", ("mtkemas_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {"mtkemas_entry": "Vstup", "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup",
                               "exit": "Výstup"}
