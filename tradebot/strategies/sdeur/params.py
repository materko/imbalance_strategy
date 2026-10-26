"""Popisy parametrov SD ZÓNY EURUSD pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🧱 Zóna (vyšší TF)"
_G1 = "🌙 Kvalita zóny"
_G2 = "🎯 Vstup (čas New York)"
_G3 = "🛡️ Stop a cieľ"
_G4 = "💰 Veľkosť"
_G5 = "🎨 Vizualizácia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "zoneTF": dict(group=_G0, title="TF zóny (min)",
                   tooltip="Na akom TF sa hľadajú zóny (60 = hodinové). Sviečky sa skladajú zo sviečok grafu; vstup sa hľadá na grafe (5m)."),
    "atrLen": dict(group=_G0, title="ATR zóny (dĺžka)", tooltip="ATR na TF zóny — jednotka výšky zóny, odchodu a rezervy stopu."),
    "baseMaxBars": dict(group=_G0, title="Báza najviac (sviečok)", tooltip="Báza = 1 až toľko sviečok TF zóny, knôt po knôt."),
    "baseMax": dict(group=_G0, title="Báza najviac vysoká", tooltip="Vyššia báza nie je báza, ale pohyb."),
    "extremeBars": dict(group=_G0, title="Báza na extréme (sviečok pred ňou)",
                        tooltip="Supply musí byť vrcholom, demand dnom posledných toľkých sviečok TF zóny. 0 = nekontroluje sa."),
    "depMin": dict(group=_G0, title="Odchod aspoň", tooltip="O koľko musí cena odísť od bázy (supply: low pod spodnou hranou)."),
    "depMaxBars": dict(group=_G0, title="Odchod najneskôr do (sviečok)",
                       tooltip="Rýchly odchod = silná zóna. Keď cena bázu medzitým prerazí, zóna nevznikne."),
    "minZoneHeight": dict(group=_G1, title="Výška zóny min (0 = bez)", inline="zh",
                          tooltip="Príliš úzka zóna = stop v šume a poplatok je veľká časť rizika."),
    "maxZoneHeight": dict(group=_G1, title="max", inline="zh", tooltip="Príliš široká zóna = ďaleký stop."),
    "zoneMaxHours": dict(group=_G1, title="Zóna platí (hodín)", tooltip="Po toľkých hodinách od vzniku zóna zanikne."),
    "useFormWindow": dict(group=_G1, title="Len zóny z okna vzniku",
                          tooltip="Zóna, ktorej posledná sviečka bázy vznikla v okne (default noc 18–2 NY = Ázia)."),
    "formStartH": dict(group=_G1, title="Vznik od (H)", inline="fw", tooltip="Hodina New York; cez polnoc sa okno zalomí."),
    "formEndH": dict(group=_G1, title="do (H)", inline="fw", tooltip="Hodina New York (bez nej)."),
    "allowLong": dict(group=_G2, title="Long z demand zón", tooltip="Limitka na kúpu pri návrate do demand zóny."),
    "allowShort": dict(group=_G2, title="Short zo supply zón", tooltip="Limitka na predaj pri návrate do supply zóny."),
    "entryStartH": dict(group=_G2, title="Vstupy od (H)", inline="es", tooltip="Londýn: 2:00 NY = 8:00 SK."),
    "entryStartM": dict(group=_G2, title="M", inline="es", tooltip="Minúta."),
    "entryEndH": dict(group=_G2, title="Vstupy do (H)", inline="ee",
                      tooltip="Prvý dotyk zóny mimo okna zónu minie bez obchodu (už to nie je prvý návrat)."),
    "entryEndM": dict(group=_G2, title="M", inline="ee", tooltip="Minúta."),
    "entryDepthPct": dict(group=_G2, title="Limitka v hĺbke zóny (%)", step=5,
                          tooltip="0 = na bližšej hrane (najčastejšie vyplnenie), 50 = v strede (lepšia cena, menej obchodov)."),
    "maxTradesPerDay": dict(group=_G2, title="Max obchodov za deň (0 = bez)", tooltip="Deň New York."),
    "slBuffer": dict(group=_G3, title="Rezerva SL za zónou", tooltip="Stop = vzdialenejšia hrana + rezerva + 1 tick."),
    "rrRatio": dict(group=_G3, title="RRR (cieľ = RR × riziko)", step=0.1, tooltip="1 : 1, 1 : 2, 1 : 3 …"),
    "maxHoldHours": dict(group=_G3, title="Zavrieť po (hodinách, 0 = nie)", tooltip="Obchod, ktorý nedošiel do stopu ani cieľa, sa zavrie trhom."),
    "fixedQty": dict(group=_G4, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G4, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte; 6E: 1 pip = 12,5 $."),
    "showZones": dict(group=_G5, title="Kresliť zóny", tooltip="Box zóny od bázy po jej minutie."),
    "leverage": dict(group=_G6, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
