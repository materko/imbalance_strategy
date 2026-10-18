"""Popisy parametrov TKS 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_GK = "🧭 NQ Kompas"
_GP = "🎯 Pravidlá"
_GT = "⏱️ Časové okno"
_GS = "🛡️ Stop loss"
_GR = "💰 Veľkosť"
_GX = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filtre"

GROUPS: tuple[str, ...] = (_GK, _GP, _GT, _GS, _GR, _GX, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "lookbackDays": dict(group=_GK, title="Pásmo šumu z (dní)",
                         tooltip="Zložka „únik zo šumu“: pohyb od otvorenia voči priemeru z toľkých predošlých dní pre tú istú minútu."),
    "loLevel": dict(group=_GP, title="Short pod (Kompas)", step=1.0,
                    tooltip="Short, keď Kompas zavrie pod touto hranicou toľko sviečok po sebe, koľko je „Sviečok po sebe“."),
    "hiLevel": dict(group=_GP, title="Long nad (Kompas)", step=1.0,
                    tooltip="Long, keď Kompas zavrie nad touto hranicou toľko sviečok po sebe."),
    "nConf": dict(group=_GP, title="Sviečok po sebe", tooltip="Koľko zavretí po sebe musí byť za hranicou (zadanie: 3)."),
    "rrRatio": dict(group=_GP, title="RR (TP = RR × SL)", step=0.1, tooltip="Cieľ ako násobok vzdialenosti SL (minimum 0,5)."),
    "pivLen": dict(group=_GP, title="Swing: sviečok na každej strane",
                   tooltip="SL na najbližší swing high (short) / low (long) za cenou, potvrdený toľkými sviečkami vľavo aj vpravo."),
    "maxTradesPerSession": dict(group=_GP, title="Max. obchodov za seansu (0 = bez limitu)", tooltip="Seansa 9:30–16:00 NY."),
    "closeAtSessionEnd": dict(group=_GP, title="Zatvoriť o 16:00 NY", tooltip="Pravidlá testovania: vypnuté (drží do SL / TP)."),
    "tradeDirection": dict(group=_GP, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "entryStartMin": dict(group=_GT, title="Vstupy od (min po 9:30)", tooltip="0 = od 9:30; 60 = od 10:30."),
    "entryEndMin": dict(group=_GT, title="Vstupy do (min po 9:30)", tooltip="390 = do 16:00; 330 = do 15:00."),
    "pauseFromMin": dict(group=_GT, title="Prestávka od (min po 9:30)", tooltip="Napr. 150 = 12:00. Rovnaké ako „do“ = vypnuté."),
    "pauseToMin": dict(group=_GT, title="Prestávka do (min po 9:30)", tooltip="Napr. 180 = 12:30."),
    "slMode": dict(group=_GS, title="Typ SL", tooltip="swing = najbližší swing za cenou (zadanie); atr = násobok ATR; points = pevné body."),
    "slAtrMult": dict(group=_GS, title="SL: násobok ATR", step=0.25, tooltip="Pri type atr."),
    "slPoints": dict(group=_GS, title="SL: body", step=5.0, tooltip="Pri type points (MNQ / NQ body)."),
    "atrLen": dict(group=_GS, title="ATR dĺžka", tooltip="ATR grafu pre SL a strop."),
    "maxSlPoints": dict(group=_GS, title="Strop SL (body, 0 = bez)", step=5.0, tooltip="Obchod so vzdialenejším SL sa vynechá."),
    "maxSlAtr": dict(group=_GS, title="Strop SL (× ATR, 0 = bez)", step=0.5, tooltip="Obchod so vzdialenejším SL sa vynechá."),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov", tooltip="Zapnuté = qty; vypnuté = veľkosť z rizika v $ k SL."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "leverage": dict(group=_GX, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
