"""Metadáta Trendline Breakout pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

#: Stratégia nemá Pine predlohu, takže nie je čo odoberať ani odchyľovať.
REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "minTouches": "Klasické pravidlo: dva body sú len sklon, platná trendovka má tri dotyky. "
                  "Tretí môže prísť aj po vzniku čiary — obchoduje sa až potom.",
    "entryMode": "close má najviac obchodov, retest najtesnejší stop a najmenej falošných "
                 "prerazení — ktorý je lepší, povie meranie.",
    "lineTF": "Materiály odporúčajú trendovky na vyššom TF (1h a viac); na 5m grafe sa dá "
              "kresliť od 5m, ale čím nižší TF, tým viac šumu.",
    "maxSlopeAtr": "Prudké čiary (nad ~60°) sa podľa praxe lámu rýchlo a prerazenie často "
                   "prejde do bočného pohybu — strop sklonu ich odfiltruje.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["useTradeWindow"],
     "params": ["tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM", "closeAtWindowEnd"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("lines", "Trendovky", ("tl_resistance", "tl_support"), "#6366f1"),
    ChartLayer("pivots", "Pivoty", ("tl_pivot",), "#94a3b8"),
    ChartLayer("breaks", "Prerazenia", ("tl_break",), "#6366f1"),
    ChartLayer("entries", "Vstupy", ("tl_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "tl_resistance": "Odpor (trendovka)",
    "tl_support": "Podpora (trendovka)",
    "tl_pivot": "Pivot",
    "tl_break": "Prerazenie",
    "tl_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
