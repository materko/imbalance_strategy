"""Metadáta Breakoutu pre webapp — vrstvy grafu, závislosti prepínačov, poznámky k poliam."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "openingMinutes": "Sviečka prichádza z informatívneho TF (5m alebo 15m), nie z barov grafu. "
                      "Vo Freqtrade si ho adaptér poskladá z 1m sám; v MultiCharts musí byť na "
                      "grafe ako Data2.",
    "orderType": "Signál je pri oboch ten istý — líši sa len cena plnenia. Rozdiel v počte "
                 "obchodov medzi market a limit je cena za lepší vstup a patrí do záveru.",
    "sessionStartH": "Čas je v pásme America/New_York, nie v SEČ: prechod na letný čas majú USA "
                     "a Európa v iný týždeň a pevný posun by tie dva týždne obchodoval vedľa.",
    "maxTradesPerDay": "Počíta sa zadaný príkaz, nie vyplnený obchod. Pri type limit teda deň, "
                       "v ktorom sa retest nevrátil, skončí bez obchodu.",
    "entryWindowMinutes": "Na indexoch má prvá hodina po otvorení iný charakter než zvyšok dňa; "
                          "toto okno je to, čím sa to dá oddeliť.",
}

#: Prepínač -> podnastavenia, ktoré sa vo formulári zbalia pod neho.
FEATURES: list[dict[str, Any]] = [
    {"switches": ["useVolumeFilter"], "params": ["volSmaLen", "volMultiplier"]},
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["showRange"], "params": []},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("opening", "Otváracia sviečka", ("bo_box",), "#f59e0b"),
    ChartLayer("levels", "Hranice (high / low)", ("bo_high", "bo_low"), "#f59e0b"),
    ChartLayer("entries", "Vstupy", ("bo_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "bo_box": "Otváracia sviečka",
    "bo_high": "Open high",
    "bo_low": "Open low",
    "bo_entry": "Vstup (prerazenie)",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
