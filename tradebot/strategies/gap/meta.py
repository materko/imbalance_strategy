"""Metadáta Gap Fill pre webapp — vrstvy grafu a závislosti prepínačov."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

#: Čo z parametra nie je vidieť na jeho titulku — hlavne to, kedy vôbec platí.
PARAM_NOTES: dict[str, str] = {
    "maxGapAtr": "Meranie na 2 791 dňoch NQ: medzera pod 0,3 ATR sa vyplní v 77,8 % dní, "
                 "0,3–0,7 ATR v 42 %, nad 1,2 ATR už len v 8,2 %.",
    "requireInsideRange": "Otvorenie vnútri včerajšieho rozsahu sa vypĺňa v 70,4 % dní, "
                          "mimo neho v 44–47 %.",
    "confirmMinutes": "Platí pri entryMode = confirm alebo retest. S potvrdením prvej 15m "
                      "sviečky stúpa výplň malých medzier zo 77,8 % na 93,1 %.",
    "slAtrMult": "Platí pri slMode = atr. Pohyb proti sebe má medián 0,34 ATR a 90. percentil "
                 "0,97 ATR — stop pod 1 ATR vypadne z bežného rozptylu.",
    "maxHoldMinutes": "Medián času do výplne je 18 minút (malé medzery 7), 90. percentil 207. "
                      "43 % výplní nastane do 10:30 newyorského času.",
    "targetPct": "Platí pri tpMode = gap. 100 % = celá výplň na včerajší close; nižšie číslo "
                 "berie len časť medzery, čo zvyšuje podiel ziskových na úkor veľkosti.",
    "rrRatio": "Platí len pri tpMode = rr.",
    "slGapMult": "Platí len pri slMode = gap_mult.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["closeAtSessionEnd"], "params": []},
    {"switches": ["showGap"], "params": []},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("gap", "Medzera", ("gap_box",), "#f59e0b"),
    ChartLayer("target", "Úroveň výplne", ("gap_target",), "#10b981"),
    ChartLayer("entries", "Vstupy", ("gap_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "gap_box": "Otváracia medzera",
    "gap_target": "Úroveň výplne (včerajší close)",
    "gap_entry": "Vstup (výplň medzery)",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
