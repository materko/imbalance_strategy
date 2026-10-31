"""Popisy parametrov ORB 15/5 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕘 Opening range (New York, HHMM)"
_G1 = "🎯 Vstup a filtre"
_G2 = "🛡️ Cieľ a koniec"
_G3 = "💰 Veľkosť"
_G4 = "🎨 Vizualizácia"
_G5 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "orStart": dict(group=_G0, title="Začiatok OR (HHMM)", inline="or", tooltip="Predloha: 930 = 9:30 New York."),
    "orMinutes": dict(group=_G0, title="Dĺžka OR (min)", inline="or", tooltip="Predloha: 15 — tri 5m sviečky."),
    "lastEntry": dict(group=_G0, title="Bez vstupov po (HHMM)", tooltip="Od tohto času nový obchod nie; pri zapnutom zavretí aj koniec pozície."),
    "allowLong": dict(group=_G1, title="Long", inline="dir", tooltip="Predloha predvolene vypnuté."),
    "allowShort": dict(group=_G1, title="Short", inline="dir", tooltip="Predloha predvolene vypnuté."),
    "maxTradesPerDay": dict(group=_G1, title="Max obchodov za deň", tooltip="Predloha: 1."),
    "useWickFilter": dict(group=_G1, title="Filter knôtu", inline="wk", tooltip="Odmietne prieraz, ktorého knôt proti smeru je veľký."),
    "maxWickPct": dict(group=_G1, title="Knôt najviac (% sviečky)", inline="wk", tooltip="Long: spodný knôt, short: horný."),
    "useDailyBias": dict(group=_G1, title="Filter predošlého dňa", inline="bias",
                         tooltip="Zavretie pod low predošlého dňa = bez longov, nad high = bez shortov."),
    "biasCheck": dict(group=_G1, title="Čas kontroly (HHMM)", inline="bias", tooltip="Predloha: 915 — v praxi prvý bar po OR."),
    "targetMode": dict(group=_G2, title="Cieľ", options=[0, 1], tooltip="0 = RR × stop, 1 = pevné body."),
    "rr": dict(group=_G2, title="RR", inline="tp", step=0.25, tooltip="Predloha: 2."),
    "targetPoints": dict(group=_G2, title="Cieľ (body)", inline="tp", tooltip="Len pri cieli v bodoch."),
    "closeAtEnd": dict(group=_G2, title="Zavrieť po poslednom vstupe", tooltip="Predloha: zapnuté (16:00 NY)."),
    "riskDollar": dict(group=_G3, title="Riziko na obchod ($)", tooltip="Predloha: 500 $."),
    "drawRange": dict(group=_G4, title="Kresliť OR", tooltip="Box opening range."),
    "leverage": dict(group=_G5, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
