"""Popisy parametrov DAILY OPEN pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕛 Úroveň (čas New York)"
_G1 = "🚀 Vstup"
_G2 = "🚪 Výstup"
_G3 = "💰 Veľkosť"
_G4 = "🎨 Vizualizácia"
_G5 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "refH": dict(group=_G0, title="Úroveň = zavretie sviečky o (H)", inline="ref",
                 tooltip="Close sviečky, ktorá sa zavrie v tomto čase. Video: polnoc (0:00)."),
    "refM": dict(group=_G0, title="M", inline="ref", tooltip="Minúta."),
    "breakPts": dict(group=_G1, title="Prah nad úrovňou (body)", tooltip="Long nad zavretím + prah. Video: 30."),
    "entryMode": dict(group=_G1, title="Vstup",
                      tooltip="stop = stop order na úrovni prierazu (platí do konca okna); "
                              "close = market na zavretí sviečky nad úrovňou."),
    "breakMode": dict(group=_G1, title="Prieraz zavretia",
                      tooltip="any = stačí prieraz zavretie + prah v okne vstupu; before = cena musí byť nad "
                              "zavretím polnoci už pred začiatkom okna (v noci)."),
    "entryStartH": dict(group=_G1, title="Vstup od (H)", inline="es", tooltip="Video: 8:00 NY."),
    "entryStartM": dict(group=_G1, title="M", inline="es", tooltip="Minúta."),
    "entryEndH": dict(group=_G1, title="Vstup do (H)", inline="ee", tooltip="Potom sa nevyplnený order zruší."),
    "entryEndM": dict(group=_G1, title="M", inline="ee", tooltip="Minúta."),
    "tradeDirection": dict(group=_G1, title="Smer", tooltip="Video: len long. Both / Short only = short pod zavretím − prah."),
    "maxTradesPerDay": dict(group=_G1, title="Max. obchodov za deň", tooltip="Video: 1."),
    "weekdaysOnly": dict(group=_G1, title="Len pondelok–piatok", tooltip="Cez víkend sa nevstupuje."),
    "slPts": dict(group=_G2, title="Stop (body)", tooltip="Video: 1 000 $ na NQ = 50 bodov."),
    "tpPts": dict(group=_G2, title="Cieľ (body, 0 = bez cieľa)", tooltip="Video: bez cieľa, výstup v čase."),
    "exitH": dict(group=_G2, title="Výstup o (H)", inline="ex", tooltip="Zatvorenie na zavretí sviečky v tomto čase. Video: 16:00."),
    "exitM": dict(group=_G2, title="M", inline="ex", tooltip="Minúta."),
    "fixedQty": dict(group=_G3, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G3, title="Počet kontraktov", tooltip="Video: 1 NQ."),
    "riskDollar": dict(group=_G3, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte."),
    "showLevels": dict(group=_G4, title="Kresliť úroveň a prieraz", tooltip="Zavretie polnoci a úroveň prierazu."),
    "leverage": dict(group=_G5, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
