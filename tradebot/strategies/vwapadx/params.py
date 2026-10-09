"""Popisy parametrov VWAP ADX pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G1 = "🕐 Opening range a čas (CT)"
_G2 = "📈 VWAP a ADX"
_G3 = "🎯 TP / SL a obchody"
_G4 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G1, _G2, _G3, _G4, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "orStartHHMM": dict(group=_G1, title="Opening range od (HHMM CT)",
                        tooltip="Začiatok opening rangu v čase Chicaga (830 = 8:30 CT = 9:30 New York). Od prvého "
                                "baru v tomto čase alebo neskôr sa každý deň začína nový range."),
    "orEndHHMM": dict(group=_G1, title="Opening range do (HHMM CT)",
                      tooltip="Koniec opening rangu (900 = 9:00 CT). Bar o tomto čase už do rangu nepatrí; od neho "
                              "sa hľadá prerazenie."),
    "exitHHMM": dict(group=_G1, title="Časový exit (HHMM CT)",
                     tooltip="Otvorená pozícia sa zatvorí na zavretí baru, ktorý sa zatvára v tomto čase alebo "
                             "neskôr. Signály sa berú len zo sviečok, ktoré sa zatvoria skôr."),
    "vwapAnchor": dict(group=_G2, title="Ukotvenie VWAP",
                       tooltip="RTH 8:30 CT = VWAP od začiatku opening rangu (beží aj cez večer až do ďalšieho "
                               "rangu). Polnoc CT = od polnoci Chicaga. VWAP potrebuje skutočný objem (MNQ áno, "
                               "CFD len odhad)."),
    "adxLen": dict(group=_G2, title="ADX dĺžka",
                   tooltip="Dĺžka DI aj vyhladenia ADX (Pine ta.dmi), na baroch grafu."),
    "adxMin": dict(group=_G2, title="ADX minimum",
                   tooltip="Vstup len keď je ADX nad týmto prahom a zároveň nestúpa oproti predošlej sviečke — "
                           "kým ADX ešte rastie, čaká sa."),
    "tpBars": dict(group=_G3, title="TP = high posledných N sviečok",
                   tooltip="Cieľ = najvyšší high posledných N barov vrátane signálnej sviečky. Je to pevná úroveň."),
    "slBars": dict(group=_G3, title="SL = low posledných N sviečok",
                   tooltip="Stop = najnižší low posledných N barov vrátane signálnej sviečky. Pevná úroveň."),
    "maxTrades": dict(group=_G3, title="Max obchodov za deň",
                      tooltip="Koľko vstupov od začiatku opening rangu. Každý ďalší potrebuje nový dotyk VWAP."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)",
                       tooltip="Koľko dolárov stojí stop; veľkosť pozície sa dopočíta zo vzdialenosti stopu. Pine "
                               "má natvrdo 1 kontrakt."),
    "legacyPineSizing": dict(group=_G4, title="Pine veľkosť (1 kontrakt)",
                             tooltip="Vždy 1 kontrakt ako v Pine, bez ohľadu na riziko."),
    "leverage": dict(group=_G4, title="Páka (Freqtrade)",
                     tooltip="Páka vo Freqtrade futures. Na MultiCharts bez účinku."),
    "showVwap": dict(group=_G4, title="Kresliť VWAP", tooltip="Čiara VWAP v grafe behu (bod každých 5 minút)."),
    "showRange": dict(group=_G4, title="Kresliť opening range", tooltip="Box opening rangu až po časový exit."),
}

PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
