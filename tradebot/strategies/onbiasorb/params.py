"""Popisy parametrov Overnight Bias ORB pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G1 = "🕐 Čas (CT)"
_G2 = "🛡️ SL / TP"
_G3 = "📈 ADX"
_G4 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G1, _G2, _G3, _G4, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "onStartHHMM": dict(group=_G1, title="Overnight range od (HHMM CT)",
                        tooltip="Začiatok overnight rangu: 0 = polnoc, 2300 = 23:00 predošlého dňa (vo videu oboje)."),
    "rthHHMM": dict(group=_G1, title="Open trhu (HHMM CT)",
                    tooltip="Koniec overnight rangu a začiatok 15m opening rangu (830 = 8:30 CT = 9:30 New York)."),
    "exitHHMM": dict(group=_G1, title="Časový exit (HHMM CT)",
                     tooltip="Od tohto času sa nevstupuje a otvorená pozícia sa zatvorí (1430 = 14:30 CT)."),
    "minEntryHHMM": dict(group=_G1, title="Najskorší signál (HHMM CT)",
                         tooltip="Signál len zo sviečky, ktorá sa zatvára v tomto čase alebo neskôr (900 = 9:00 CT)."),
    "atrLen": dict(group=_G2, title="Dĺžka ATR", tooltip="ATR za toľko seáns (alebo denných sviečok)."),
    "avgLen": dict(group=_G2, title="Priemer ATR za N seáns",
                   tooltip="Stop sa počíta z priemeru posledných N hodnôt ATR. Kým ich nie je N, neobchoduje sa."),
    "slPct": dict(group=_G2, title="SL (% z priem. ATR)", tooltip="Vzdialenosť stopu ako % priemerného ATR."),
    "rr": dict(group=_G2, title="TP = násobok SL", step=0.5, tooltip="Cieľ = toľkonásobok vzdialenosti stopu."),
    "atrSource": dict(group=_G2, title="Zdroj ATR",
                      tooltip="Seansa 0:00–16:00 CT = ako vo videu. Denné sviečky burzy = denný ATR burzy, hodnota "
                              "z včerajška."),
    "adxLen": dict(group=_G3, title="ADX dĺžka", tooltip="Dĺžka DI aj vyhladenia ADX (Pine ta.dmi), na 15m baroch."),
    "adxMin": dict(group=_G3, title="ADX minimum", tooltip="Vstup len keď je ADX nad týmto prahom."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)",
                       tooltip="Veľkosť pozície z rizika. Pine má natvrdo 1 kontrakt."),
    "legacyPineSizing": dict(group=_G4, title="Pine veľkosť (1 kontrakt)", tooltip="Vždy 1 kontrakt ako v Pine."),
    "leverage": dict(group=_G4, title="Páka (Freqtrade)", tooltip="Páka vo Freqtrade futures. Na MultiCharts bez účinku."),
    "showLevels": dict(group=_G4, title="Kresliť rangy", tooltip="Overnight range s tretinami a opening range v grafe."),
}

PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
