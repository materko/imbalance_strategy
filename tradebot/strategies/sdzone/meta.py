"""Metadáta SD Zones pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "requireFresh": "Jadro metodiky. Predpoklad je, že pri prvom dotyku sa nevyplnené "
                    "objednávky vyčerpajú a zóna stratí význam. Vypnutie to zmení na obyčajné "
                    "obchodovanie úrovní — dá viac obchodov, ale je to už iná myšlienka.",
    "impulseMinBodyAtr": "Hlavná páka na kvalitu zóny. Slabý odchod znamená, že tam objednávky "
                         "neboli a zóna je len čiara na grafe.",
    "zoneMode": "pfz dáva lepšiu cenu a tesnejší stop, ale cenu častejšie minie; wfz sa vyplní "
                "skoro vždy, zato s horším pomerom rizika. Ktoré je lepšie, povie meranie.",
    "rrRatio": "Stop ide za celú zónu, takže je široký. Pri RR pod 2 sa to obvykle nezaplatí.",
    "useTrendFilter": "Najjednoduchšia náhrada za kontext vyššieho timeframu, s ktorým metodika "
                      "pracuje. Nie je to to isté — je to to, čo sa dá zmerať.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["enableTrailing"], "params": ["trailActivationR", "trailOffsetR"]},
    {"switches": ["useTrendFilter"], "params": ["trendMaLen"]},
    {"switches": ["useTradeWindow"],
     "params": ["tradeTZ", "tradeStartH", "tradeStartM", "tradeEndH", "tradeEndM",
                "closeAtWindowEnd"]},
    {"switches": ["showZones"], "params": ["showPatterns"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("zones", "Supply / demand zóny", ("sd_demand", "sd_supply"), "#10b981"),
    ChartLayer("patterns", "Formácie (RBR/DBD/…)", ("sd_pattern", "sd_base"), "#6366f1"),
    ChartLayer("entries", "Vstupy", ("sd_entry",), "#10b981"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "sd_demand": "Demand zóna",
    "sd_supply": "Supply zóna",
    "sd_base": "Báza",
    "sd_pattern": "Formácia",
    "sd_entry": "Vstup",
    "tp_box": "TP box",
    "sl_box": "SL box",
    "entry": "Vstup",
    "exit": "Výstup",
}
