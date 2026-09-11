"""Metadáta Range Breakout pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

#: Stratégia nemá Pine predlohu, takže nie je čo odoberať ani odchyľovať.
REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "maxWidthAtr": "Kľúčový parameter stratégie. Čím menšie číslo, tým tesnejšia konsolidácia sa "
                   "vyžaduje — menej setupov, ale čistejších. Publikované postupy uvádzajú 1,5–2,5.",
    "entryMode": "Tri profily toho istého nápadu: `close` má najviac obchodov a najnižšiu "
                 "úspešnosť, `continuation` naopak. Ktorý je na danom trhu lepší, povie meranie.",
    "boundaryMode": "`close` je odolnejšie: jeden dlhý knôt nerozšíri range a nezneplatní setup.",
    "minClosePosPct": "Odfiltruje prerazenia, ktoré skončili dlhým knôtom proti smeru — klasický "
                      "znak falošného prerazenia.",
    "maxHoldBars": "Breakout, ktorý sa do pár barov nepohol, obvykle už nepôjde; časový stop uvoľní "
                   "kapitál a skráti expozíciu.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["useTradeWindow"],
     "params": ["tradeTZ", "tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM",
                "closeAtWindowEnd"]},
    {"switches": ["showRange"], "params": ["showLevels"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("range", "Box konsolidácie", ("range_box",), "#f59e0b"),
    ChartLayer("levels", "Hranice rangu", ("range_high", "range_low"), "#f59e0b"),
    ChartLayer("breaks", "Prerazenia", ("range_break",), "#6366f1"),
    ChartLayer("entries", "Vstupy", ("range_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "range_box": "Konsolidácia",
    "range_high": "Horná hranica",
    "range_low": "Dolná hranica",
    "range_break": "Prerazenie",
    "range_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
