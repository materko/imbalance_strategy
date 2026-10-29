"""Popisy parametrov SPRÁVY pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📈 TREND po správe"
_G1 = "🔁 FADE po správe"
_G3 = "🛡️ Stop a cieľ"
_G7 = "📅 Kalendár (čas New York)"
_G4 = "💰 Veľkosť"
_G5 = "🎨 Vizualizácia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G3, _G7, _G4, _G5, _G6, _GE)

_TYPY = "FOMC, FOMC_MIN, CPI, NFP, PPI, PCE, GDP, RETAIL, JOLTS, ISM_M, ISM_S, CLAIMS"

PARAMS: dict[str, dict[str, Any]] = {
    "trendEvents": dict(group=_G0, title="Správy (čiarkou)",
                        tooltip=f"Po týchto správach sa ide v smere nohy. Typy: {_TYPY}. Prieskum: FOMC a PCE."),
    "trendFrom": dict(group=_G0, title="Noha od (min po správe)", inline="tn", tooltip="0 = od otvorenia baru správy."),
    "trendTo": dict(group=_G0, title="do", inline="tn", tooltip="Vstup na konci nohy."),
    "trendHold": dict(group=_G0, title="Držať (min)", tooltip="Výstup trhom po toľkých minútach od vstupu."),
    "fadeEvents": dict(group=_G1, title="Správy (čiarkou)",
                       tooltip=f"Po týchto správach sa ide proti nohe. Typy: {_TYPY}. Prieskum: CPI, PPI, JOLTS."),
    "fadeFrom": dict(group=_G1, title="Noha od (min po správe)", inline="fn", tooltip="0 = od otvorenia baru správy."),
    "fadeTo": dict(group=_G1, title="do", inline="fn", tooltip="Vstup na konci nohy."),
    "fadeHold": dict(group=_G1, title="Držať (min)", tooltip="Výstup trhom po toľkých minútach od vstupu."),
    "atrLen": dict(group=_G3, title="ATR grafu (dĺžka)", tooltip="Jednotka rezervy stopu a minimálnej nohy."),
    "slBuffer": dict(group=_G3, title="Rezerva stopu za nohou", tooltip="Stop = extrém nohy na strane proti pozícii + rezerva."),
    "trendStopLeg": dict(group=_G3, title="Stop TREND = N × noha (0 = za extrémom)", step=0.5, inline="sl",
                         tooltip="Vzdialenosť stopu od vstupu ako násobok veľkosti nohy."),
    "fadeStopLeg": dict(group=_G3, title="FADE", step=0.5, inline="sl",
                        tooltip="Default 10 × = len poistka: tesný stop pri návrate po CPI / PPI trh vyberie (prieskum)."),
    "minLeg": dict(group=_G3, title="Noha aspoň (0 = každá)", tooltip="Malý pohyb po správe = trh správu nebral."),
    "tpR": dict(group=_G3, title="Cieľ (R, 0 = len čas)", step=0.5, tooltip="Prieskum: výstup v čase je rovnako dobrý ako trailing."),
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
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
