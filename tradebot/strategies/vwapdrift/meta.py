"""Metadáta Drift VWAP pre webapp — vrstvy grafu, závislosti prepínačov, poznámky k poliam."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "vwapAnchor": "VWAP potrebuje skutočný objem burzy — MNQ z Databenta áno, Dukascopy CFD nie "
                  "(tam je v objeme len aktivita tickov a VWAP je odhad).",
    "vwapPeriod": "15m sviečky sa skladajú z barov grafu, takže graf musí mať TF, ktorým sa 15 delí "
                  "(1m, 3m, 5m, 15m). Rozpracovaná 15m sviečka sa do VWAP nepočíta.",
    "firstPullbackOnly": "Video obchoduje len prvý pullback. Vypnutím vznikne iná stratégia — "
                         "porovnaj ako dva behy.",
    "entryMode": "Signál (drift, odchod, dotyk VWAP) je pri všetkých rovnaký — líši sa len to, kedy a za "
                 "koľko sa vstúpi. Porovnávaj ich ako samostatné behy.",
    "everyBounce": "Video obchoduje len prvý pullback — každý odraz je iná stratégia, porovnaj ako dva behy.",
    "tradeBreakout": "Prerazenie je opak odrazu: obchoduje presne tie dotyky, ktoré odraz zahodí ako prerazené.",
    "rrRatio": "Video stop ani cieľ neuvádza — stop za pullback a RR 2 sú východisko, nie predloha.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["showVwap"], "params": []},
    {"switches": ["everyBounce"], "params": ["bounceAwayAtr", "maxBouncesPerDay"]},
    {"switches": ["tradeBreakout"], "params": ["breakoutAtr", "breakoutWithBias", "maxBreakoutsPerDay"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("vwap", "VWAP (farba = drift)", ("vd_vwap",), "#10b981"),
    ChartLayer("entries", "Vstupy", ("vd_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "vd_vwap": "VWAP",
    "vd_entry": "Vstup (pullback k VWAP)",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
