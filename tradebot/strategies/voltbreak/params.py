"""Popisy parametrov Volt Break pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G1 = "🔊 Noise hranica"
_G2 = "🎯 TP / SL a obchody"
_G3 = "🕐 Čas (CT)"
_G4 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G1, _G2, _G3, _G4, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "noisePct": dict(group=_G1, title="Noise barrier (% z priem. ATR)", step=1,
                     tooltip="Noise Up = open o polnoci CT + toľko % priemerného ATR. Long len nad touto hranicou."),
    "atrLen": dict(group=_G1, title="Dĺžka ATR",
                   tooltip="ATR za toľko seáns (alebo denných sviečok) — prvých N priemer, potom Wilderova rekurzia."),
    "avgLen": dict(group=_G1, title="Priemer ATR za N seáns",
                   tooltip="Noise sa počíta z priemeru posledných N hodnôt ATR. Kým ich nie je N, neobchoduje sa."),
    "atrSource": dict(group=_G1, title="Zdroj ATR",
                      tooltip="Seansa 0:00–16:00 CT = ako vo videu (seansa od polnoci po koniec obchodného dňa). "
                              "Denné sviečky burzy = denný ATR burzy (deň od 17:00 CT), hodnota z včerajška."),
    "tpUsd": dict(group=_G2, title="Take profit ($ na kontrakt)",
                  tooltip="Cieľ v dolároch na 1 kontrakt NQ (prepočet na body cez 'USD za bod')."),
    "slUsd": dict(group=_G2, title="Stop loss ($ na kontrakt)",
                  tooltip="Stop v dolároch na 1 kontrakt NQ (prepočet na body cez 'USD za bod')."),
    "maxTrades": dict(group=_G2, title="Max obchodov za deň",
                      tooltip="Po výstupe môže prísť ďalší vstup, kým podmienky platia, najviac toľkoto za deň."),
    "startHHMM": dict(group=_G3, title="Začiatok vstupov (HHMM CT)",
                      tooltip="Signál len zo sviečky, ktorá sa zatvára v tomto čase alebo neskôr (1000 = 10:00 CT)."),
    "endHHMM": dict(group=_G3, title="Koniec vstupov a zatvorenie (HHMM CT)",
                    tooltip="Od tohto času sa nevstupuje a otvorená pozícia sa zatvorí (1430 = 14:30 CT)."),
    "usdPerPoint": dict(group=_G4, title="USD za bod (pre TP/SL)",
                        tooltip="Pine prepočíta TP/SL v $ cez hodnotu bodu grafu. Skript je na NQ (20 $/bod), takže "
                                "800 $ = 40 bodov. Na MNQ (2 $/bod) by doslovne vyšlo 400 bodov — preto 20."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)",
                       tooltip="Veľkosť pozície z rizika. 150 $ = 1 MNQ pri stope 75 bodov (1/10 NQ)."),
    "legacyPineSizing": dict(group=_G4, title="Pine veľkosť (1 kontrakt)", tooltip="Vždy 1 kontrakt ako v Pine."),
    "leverage": dict(group=_G4, title="Páka (Freqtrade)", tooltip="Páka vo Freqtrade futures. Na MultiCharts bez účinku."),
    "showLevels": dict(group=_G4, title="Kresliť Noise Up a VWAP", tooltip="Čiary v grafe behu."),
}

PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
