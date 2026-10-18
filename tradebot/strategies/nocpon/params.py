"""Popisy parametrov NOC + PONDELOK pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🌙 Noc (čas New York)"
_G1 = "📅 Pondelok (čas New York)"
_G2 = "📈 Trend"
_G3 = "🔁 Roll kontraktu"
_G4 = "🛡️ Poistka"
_G5 = "💰 Veľkosť"
_G6 = "🎨 Vizualizácia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "useNight": dict(group=_G0, title="Obchodovať noc", tooltip="Long od večera do rána (zisk Nasdaqu vzniká hlavne mimo seansy)."),
    "nightEntryH": dict(group=_G0, title="Vstup (H)", inline="ne", tooltip="Market na zavretí sviečky v tomto čase. Meranie: 15:55."),
    "nightEntryM": dict(group=_G0, title="M", inline="ne", tooltip="Minúta."),
    "nightExitH": dict(group=_G0, title="Výstup (H)", inline="nx",
                       tooltip="V nasledujúci obchodný deň (piatok → pondelok). Meranie: 3:00 — úsek 3:00–9:30 už nepridáva."),
    "nightExitM": dict(group=_G0, title="M", inline="nx", tooltip="Minúta."),
    "useMonday": dict(group=_G1, title="Obchodovať pondelok", tooltip="Long cez pondelkovú seansu — jediný deň s jasne kladným priemerom."),
    "monEntryH": dict(group=_G1, title="Vstup (H)", inline="me", tooltip="Meranie: 9:30."),
    "monEntryM": dict(group=_G1, title="M", inline="me", tooltip="Minúta."),
    "monExitH": dict(group=_G1, title="Výstup (H)", inline="mx",
                     tooltip="Meranie: 15:55. Keď v tom čase začína noc, pozícia sa len predĺži do rána."),
    "monExitM": dict(group=_G1, title="M", inline="mx", tooltip="Minúta."),
    "useTrend": dict(group=_G2, title="Len v rastovom trende",
                     tooltip="Vstup len keď je denné zavretie nad SMA denných zavretí (pondelok: piatkové). Vypína rok 2022."),
    "smaLen": dict(group=_G2, title="SMA denných zavretí (dni)", tooltip="Meranie: 100; 50–200 dáva podobný výsledok."),
    "closeRefH": dict(group=_G2, title="Denné zavretie o (H)", inline="cr", tooltip="Cena v tomto čase je denné zavretie pre SMA."),
    "closeRefM": dict(group=_G2, title="M", inline="cr", tooltip="Minúta."),
    "skipRoll": dict(group=_G3, title="Vynechať noci pri rolle",
                     tooltip="Marec / jún / september / december: v spojitých dátach je v noc rollu skok medzi kontraktmi."),
    "rollFromDay": dict(group=_G3, title="Od dňa v mesiaci", inline="rl", tooltip="Prvý vynechaný deň."),
    "rollToDay": dict(group=_G3, title="do dňa", inline="rl", tooltip="Posledný vynechaný deň."),
    "stopPct": dict(group=_G4, title="Stop (% ceny, 0 = bez stopu)", step=0.1,
                    tooltip="Voliteľná poistka proti gapu. Meranie bolo bez stopu."),
    "fixedQty": dict(group=_G5, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $ (potrebuje stop)."),
    "qty": dict(group=_G5, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte."),
    "showSma": dict(group=_G6, title="Kresliť SMA denných zavretí", tooltip="Úroveň SMA na každom dennom zavretí."),
    "leverage": dict(group=_G7, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
