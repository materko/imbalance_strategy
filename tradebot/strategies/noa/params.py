"""Popisy parametrov NOA 1.0 — Noise Area (Concretum) pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "⚙️ Pásmo šumu"
_G1 = "⏱️ Kontroly a výstup"
_GX = "🚪 Poistka, smer, počet"
_GR = "💰 Veľkosť"
_GV = "🎨 Vizualizácia"
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filtre"

GROUPS: tuple[str, ...] = (_G0, _G1, _GX, _GR, _GV, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "lookbackDays": dict(group=_G0, title="Pásmo šumu z (dní)",
                         tooltip="Pásmo pre každú minútu seansy = priemerný pohyb od otvorenia (|close / open − 1|) "
                                 "v tej istej minúte za toľko predošlých dní. Zdroj: 14."),
    "volMult": dict(group=_G0, title="Násobok pásma", step=0.05,
                    tooltip="1 = zdroj; vyššie = širšie pásmo, menej a neskoršie vstupy."),
    "gapAdjust": dict(group=_G0, title="Hranice podľa medzery",
                      tooltip="Horná hranica od max(open, včerajšie zavretie), dolná od min — zdroj. "
                              "Vypnuté = obe od dnešného open."),
    "checkEvery": dict(group=_G1, title="Kontrola každých (min)",
                       tooltip="Vstupy aj výstupy sa rozhodujú len na zavretí baru o toľko minút od 9:30 NY "
                               "(zdroj: 30 = 10:00, 10:30, …). Medzi kontrolami sa nič nerobí."),
    "lastEntryMin": dict(group=_G1, title="Posledný vstup (min po 9:30)", tooltip="360 = 15:30 NY. O 16:00 sa zatvára všetko."),
    "trailVwap": dict(group=_G1, title="Výstup aj cez VWAP",
                      tooltip="Long sa na kontrole zavrie pod max(horná hranica, VWAP), short nad min(dolná, VWAP) — zdroj. "
                              "Vypnuté = len pod / nad hranicou pásma."),
    "hardStopPct": dict(group=_GX, title="Poistka: pevný stop (% z ceny)", step=0.1,
                        tooltip="Stop u brokera len proti prudkému pohybu medzi kontrolami — zdroj ho nemá. "
                                "1 % ≈ 250 bodov MNQ. 0 = 10 % (prakticky bez stopu)."),
    "tradeDirection": dict(group=_GX, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_GX, title="Max. vstupov za deň",
                            tooltip="Zdroj strop nemá — po výstupe smie na ďalšej kontrole vstúpiť znova."),
    "weekdaysOnly": dict(group=_GX, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov",
                     tooltip="Zapnuté = qty kontraktov; vypnuté = veľkosť z rizika v $ k pevnému stopu (poistke)."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika — počíta sa k poistke."),
    "showLevels": dict(group=_GV, title="Kresliť hranice a úroveň výstupu",
                       tooltip="Hranice pásma na každej kontrole a úroveň, pod ktorou sa pozícia na ďalšej kontrole zavrie."),
    "showVwap": dict(group=_GV, title="Kresliť VWAP", tooltip="Seansový VWAP od 9:30 NY."),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
