"""Metadáta MTK ZONE pre webapp."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "minConf": "Bez filtra potvrdení (1) dal Pine na MNQ 5m 1 384 obchodov s PF 0,88 — priveľa zón.",
    "usePocZone": "POC sa posúva so sviečkami — zóny priamo na POC vznikajú stále znova.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["useZ1"], "params": ["zoneTf1"]},
    {"switches": ["useZ2"], "params": ["zoneTf2"]},
    {"switches": ["usePocZone"], "params": ["pocEvery"]},
    {"switches": ["useIBS"], "params": ["imbLookback", "minImbSize", "imbMaxDistTicks", "st1Max", "st2Max",
                                        "st2ConfTicks", "st3Max", "st5Max", "ibsSlLookback", "showIbsDraw"]},
    {"switches": ["usePin"], "params": ["pbRatio", "pbBodyPos", "pbMinRange"]},
    {"switches": ["useSess"], "params": ["sessStart", "sessEnd"]},
    {"switches": ["fixedQty"], "params": ["qty"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Zóny", ("mz_zone",), "#1de9b6"),
    ChartLayer("ibs", "Kroky IBS", ("mz_ifvg", "mz_cb", "mz_retest"), "#c026d3"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "mz_zone": "Zóna", "mz_ifvg": "IBS iFVG (gap)", "mz_cb": "IBS CB (potvrdenie)", "mz_retest": "IBS retest",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
