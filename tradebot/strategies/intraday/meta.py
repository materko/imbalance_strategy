"""Metadáta INTRADAY 1.0 pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "liqMode": "Smernica: „zaujíma nás likvidita, ktorá je v protismere: keď je daily bias long, hľadáme nižšiu likviditu“.",
    "entryTF": "Smernica: 1H zóny so silným impulzom → 15m zóny v 1H zónach → to isté na 5m → limitka.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useExitTime"], "params": ["exitH", "exitM"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "SD zóny 1H / 15m / 5m", ("id_zone",), "#3b82f6"),
    ChartLayer("liquidity", "PDH / PDL", ("id_liq", "id_sweep"), "#94a3b8"),
    ChartLayer("entries", "Vstupy", ("id_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "id_zone": "SD zóna", "id_liq": "PDH / PDL", "id_sweep": "Zobratie likvidity", "id_entry": "Vstup",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
