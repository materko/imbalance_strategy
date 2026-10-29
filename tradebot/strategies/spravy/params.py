"""Popisy parametrov SPRÁVY pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

from .calendar import TYPES
from .config import RULES

_GU = "✅ Obchodované správy"
_GR = [f"📰 Pravidlo {n}" for n in range(1, RULES + 1)]
_NAZVY = {"FOMC": "FOMC (rozhodnutie Fedu)", "FOMC_MIN": "Zápisnica FOMC", "CPI": "CPI (inflácia)", "NFP": "NFP (zamestnanosť)",
          "PPI": "PPI (ceny výrobcov)", "PCE": "PCE (inflácia Fedu)", "GDP": "HDP", "RETAIL": "Maloobchodné tržby",
          "JOLTS": "JOLTS (voľné miesta)", "ISM_M": "ISM výroba", "ISM_S": "ISM služby", "CLAIMS": "Žiadosti o podporu (štvrtok)"}
_G3 = "🛡️ Stop a cieľ"
_G7 = "📅 Kalendár (čas New York)"
_G4 = "💰 Veľkosť"
_G5 = "🎨 Vizualizácia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_GU, *_GR, _G3, _G7, _G4, _G5, _G6, _GE)

_TYPY = "FOMC, FOMC_MIN, CPI, NFP, PPI, PCE, GDP, RETAIL, JOLTS, ISM_M, ISM_S, CLAIMS"

PARAMS: dict[str, dict[str, Any]] = {
    "atrLen": dict(group=_G3, title="ATR grafu (dĺžka)", tooltip="Jednotka rezervy stopu a minimálnej nohy."),
    "slBuffer": dict(group=_G3, title="Rezerva stopu za nohou",
                     tooltip="Pri pravidle so stopom 0: stop = extrém nohy na strane proti pozícii + rezerva."),
    "minLeg": dict(group=_G3, title="Noha aspoň (0 = každá)", tooltip="Malý pohyb po správe = trh správu nebral."),
    "allowLong": dict(group=_G3, title="Longy", tooltip="Povoliť long."),
    "allowShort": dict(group=_G3, title="Shorty", tooltip="Povoliť short."),
    "newsAdd": dict(group=_G7, title="Pridať správy",
                    tooltip="„YYYY-MM-DD HH:MM TYP; …“ v čase New York — presunutá alebo chýbajúca správa."),
    "newsSkip": dict(group=_G7, title="Vynechať správy", tooltip="„YYYY-MM-DD TYP; …“ — zrušená alebo presunutá správa."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)",
                       tooltip="Pri vypnutom pevnom počte: počet kontraktov tak, aby strata na stope bola najviac toľko."),
    "sizeMinRisk": dict(group=_G4, title="Stop na výpočet veľkosti aspoň (ATR)", step=0.5,
                        tooltip="Tesný stop (malá noha) by dal priveľa kontraktov; s minimom je strata ≤ riziko a pozícia rozumná."),
    "showLegs": dict(group=_G5, title="Kresliť nohu po správe", tooltip="Box nohy s časom správy (SK aj NY)."),
    "leverage": dict(group=_G6, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
for _t in TYPES:
    PARAMS[f"use{_t}"] = dict(group=_GU, title=_NAZVY.get(_t, _t), inline=f"u{TYPES.index(_t) // 3}",
                              tooltip=f"Obchodovať {_t} — platí, len keď má {_t} aspoň jedno pravidlo nižšie.")
for _n, _g in enumerate(_GR, 1):
    PARAMS.update({
        f"r{_n}Event": dict(group=_g, title="Správa", options=["", *TYPES],
                            tooltip="Prázdne = pravidlo vypnuté. Jedna správa môže mať viac pravidiel (FOMC: pred správou, tlačovka)."),
        f"r{_n}Mode": dict(group=_g, title="Režim", options=["trend", "fade"],
                           tooltip="trend = vstup v smere nohy, fade = proti nohe."),
        f"r{_n}From": dict(group=_g, title="Noha od (min)", inline=f"r{_n}n",
                           tooltip="Minúty od správy; 0 = od otvorenia baru správy, záporné = pred správou (−60 = hodinu pred)."),
        f"r{_n}To": dict(group=_g, title="do", inline=f"r{_n}n", tooltip="Koniec nohy (minúty od správy)."),
        f"r{_n}Enter": dict(group=_g, title="Vstup v T + (min)", inline=f"r{_n}v",
                            tooltip="Vstup trhom; najskôr na konci nohy (tlačovka FOMC: noha 0 → 25, vstup 30)."),
        f"r{_n}Hold": dict(group=_g, title="Držať (min)", inline=f"r{_n}v", tooltip="Výstup trhom po toľkých minútach od vstupu."),
        f"r{_n}RR": dict(group=_g, title="RRR 1 : (0 = bez cieľa)", step=0.5, inline=f"r{_n}s",
                         tooltip="Cieľ v násobkoch rizika (vzdialenosti stopu). Kto ho nedosiahne, zavrie sa po čase držania. Najmenej 0,5."),
        f"r{_n}Stop": dict(group=_g, title="Stop = N × noha (0 = za extrémom)", step=0.5, inline=f"r{_n}s",
                           tooltip="Vzdialenosť stopu od vstupu ako násobok nohy; 10 × = len poistka (návrat po správe tesný stop vyberie)."),
    })
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
