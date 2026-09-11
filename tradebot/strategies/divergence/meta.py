"""Metadáta divergenčnej stratégie pre webapp — vrstvy grafu, závislosti prepínačov, poznámky."""

from __future__ import annotations

from typing import Any

from ..base import ChartLayer

#: Stratégia nemá Pine predlohu.
REMOVED_INPUTS: frozenset[str] = frozenset()
INTENTIONAL_DEFAULT_DIFFS: frozenset[str] = frozenset()

PARAM_NOTES: dict[str, str] = {
    "prd": "Pôvodná stratégia brala pivoty z `argrelextrema` nad celým DataFrame, teda o `prd` "
           "barov skôr, než boli potvrdené. Tu sa pivot použije až po potvrdení, takže signály "
           "prídu o `prd` barov neskôr než v pôvodnom backteste — a nie sú z budúcnosti.",
    "pullbackFilter": "Originál počítal 5m bary v protismere vnútri baru grafu (`st_down_c`). "
                      "Nižší TF sa z barov grafu poskladať nedá, preto sa berie supertrend "
                      "grafového TF; na 5m grafe je to identické.",
    "htfMinutes": "Musí byť násobkom TF grafu — engine si ho skladá z barov grafu rovnakým "
                  "pravidlom ako `tradebot/core/candles.py`.",
    "htf2Minutes": "Musí byť násobkom TF grafu a aspoň `htfMinutes`.",
    "slAtrMult": "Originál tvrdý stop prakticky nemal (−55 %); stratu strážil limit 200 $ a "
                 "výstup podľa trendu. Tu limit v dolároch = `riskDollar` a stop mu určuje veľkosť.",
    "rrRatio": "0 = bez pevného cieľa (originál mal ROI 90 %, teda nikdy). TP box sa vtedy "
               "nekreslí a analytika plánovaný RR nemá.",
    "trendExit": "Platí len pre obchod, ktorý je v strate (close na zlej strane vstupu) — "
                 "ziskový nechá trailingu, presne ako pôvodný `custom_stoploss`.",
    "beActivationPct": "Percentá z ceny vstupu. Pôvodné prahy boli z marže a násobili sa pákou "
                       "(`strat_lvrg`), čo je to isté číslo v cene.",
    "entryMode": "Pri confirm je počet pokusov daný životnosťou signálu (`signalBars`), nie "
                 "samostatným parametrom — presne ako originál, kde sa potvrdenie skúšalo každý bar, "
                 "kým `enter_long` platil.",
    "maxHoldBars": "Limit je v BAROCH grafu, nie v čase.",
}

FEATURES: list[dict[str, Any]] = [
    {"switches": ["zoneFilter"],
     "params": ["zoneSearchDiv", "zonePrd1", "zoneWindow1", "zonePrd2", "zoneWindow2", "zoneMaxPp", "zoneMaxBars",
                "showZones"]},
    {"switches": ["enableTrailing"],
     "params": ["beActivationPct", "beLockPct", "trailActivationPct", "trailOffsetPct"]},
]

LAYERS: tuple[ChartLayer, ...] = (
    ChartLayer("divs", "Divergencie", ("dv_bull", "dv_bear", "dv_line_bull", "dv_line_bear"), "#10b981"),
    ChartLayer("supertrend", "Supertrend", ("dv_st_up", "dv_st_down", "dv_st_htf"), "#6366f1"),
    ChartLayer("zones", "Divergenčné zóny HTF", ("dv_zone_bear", "dv_zone_bull"), "#ef4444"),
    ChartLayer("entries", "Vstupy", ("dv_armed", "dv_entry"), "#f59e0b"),
    ChartLayer("tpsl", "TP / SL boxy", ("tp_box", "sl_box", "entry", "exit"), "#10b981"),
)

KIND_TITLES: dict[str, str] = {
    "dv_bull": "Býčia divergencia", "dv_bear": "Medvedia divergencia",
    "dv_line_bull": "Spojnica býčej divergencie", "dv_line_bear": "Spojnica medvedej divergencie",
    "dv_st_up": "Supertrend hore", "dv_st_down": "Supertrend dole",
    "dv_st_htf": "Supertrend vyššieho TF",
    "dv_zone_bear": "Medvedia zóna (blokuje long)", "dv_zone_bull": "Býčia zóna (blokuje short)",
    "dv_armed": "Vyzbrojený vstup", "dv_entry": "Vstup (divergencia)",
    "tp_box": "TP box", "sl_box": "SL box", "entry": "Vstup", "exit": "Výstup",
}
