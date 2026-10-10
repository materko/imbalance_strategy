"""Popisy parametrov VALUE AREA REVERSION 1.0 pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_GP = "📊 Volume profile"
_GS = "🔁 Signál (únik a návrat)"
_GX = "🛡️ Stop a cieľ"
_GR = "💰 Veľkosť"
_GD = "🎨 Vizualizácia"
_GO = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu a filtre"

GROUPS: tuple[str, ...] = (_GP, _GS, _GX, _GR, _GD, _GO, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "profileSource": dict(group=_GP, title="Profil", options=["previous", "current"],
                          tooltip="previous = value area predošlej dokončenej seansy 18:00–18:00 (vo videu čistejšie signály); "
                                  "current = rozvíjajúci sa profil dnešnej seansy."),
    "profileSession": dict(group=_GP, title="Value area z", options=["globex", "ny"],
                           tooltip="globex = celá futures seansa 18:00–18:00 (video); ny = len NY seansa 9:30–16:00 — pri profile "
                                   "previous sa obchoduje VAH / VAL z NY seansy predošlého dňa."),
    "anchorH": dict(group=_GP, title="Začiatok seansy globex (hodina NY)", tooltip="Futures otvárajú o 18:00 New York."),
    "nyStartH": dict(group=_GP, title="NY seansa od: hodina", inline="ny1", tooltip="Pri value area z NY seansy (čas New York)."),
    "nyStartM": dict(group=_GP, title="minúta", inline="ny1", tooltip=""),
    "nyEndH": dict(group=_GP, title="NY seansa do: hodina", inline="ny2", tooltip="Bar, ktorý sa otvára o tomto čase, už nepatrí do profilu."),
    "nyEndM": dict(group=_GP, title="minúta", inline="ny2", tooltip=""),
    "profileRows": dict(group=_GP, title="Riadkov profilu", tooltip="Video: 60. Objem sviečky sa rozdelí rovnomerne do riadkov, ktorých sa dotkla."),
    "valueAreaPct": dict(group=_GP, title="Value area (%)", step=0.5, tooltip="Koľko objemu okolo POC tvorí value area. Video: 70 %."),
    "maxBarsOutside": dict(group=_GS, title="Návrat do (barov po úniku)", tooltip="Video: 5 barov."),
    "requireVolDecline": dict(group=_GS, title="Objem úniku musí klesať",
                              tooltip="Posledná sviečka úniku (medvedia pod VAL, býčia nad VAH) má menší objem ako predošlá — predajcovia nenasledujú cenu."),
    "reclaimVolMult": dict(group=_GS, title="Objem návratu (× posledná sviečka úniku)", step=0.1,
                           tooltip="Sviečka návratu má aspoň toľkokrát väčší objem ako posledná sviečka úniku. 0 = bez podmienky."),
    "requireEngulf": dict(group=_GS, title="Návrat musí pohltiť predošlú sviečku", tooltip="Filter z videa: telo návratu pohltí telo predošlej sviečky."),
    "tradeDirection": dict(group=_GS, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_GS, title="Max. obchodov za deň", tooltip="Denný strop vstupov."),
    "weekdaysOnly": dict(group=_GS, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "useTradeWindow": dict(group=_GS, title="Obchodné okno (NY)", tooltip="Vstupy len v zadanom čase New York."),
    "startH": dict(group=_GS, title="Okno od: hodina", inline="w1", tooltip="Začiatok vstupov (NY)."),
    "startM": dict(group=_GS, title="minúta", inline="w1", tooltip=""),
    "endH": dict(group=_GS, title="Okno do: hodina", inline="w2", tooltip="Koniec vstupov (NY)."),
    "endM": dict(group=_GS, title="minúta", inline="w2", tooltip=""),
    "slBufferAtr": dict(group=_GX, title="Rezerva stopu za extrémom úniku (ATR)", step=0.05, tooltip="Stop pod low (nad high) úniku ± rezerva."),
    "atrLen": dict(group=_GX, title="ATR dĺžka", tooltip="Len pre rezervu stopu."),
    "tpMode": dict(group=_GX, title="Cieľ", options=["va", "poc", "rr"],
                   tooltip="va = opačná hrana value area (VAH pri longu, video); poc = point of control; rr = násobok stopu."),
    "rrRatio": dict(group=_GX, title="Cieľ (násobok stopu)", step=0.25, tooltip="Pri cieli rr."),
    "minRR": dict(group=_GX, title="Min. RR", step=0.25, tooltip="Bližší cieľ ako toľko × stop = bez obchodu. 0 = vypnuté."),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "showValueArea": dict(group=_GD, title="Kresliť VAH / VAL", tooltip="Value area, z ktorej sa obchoduje."),
    "showPoc": dict(group=_GD, title="Kresliť POC", tooltip="Point of control (video: predvolene vypnutý)."),
    "showSignals": dict(group=_GD, title="Kresliť únik a signály", tooltip="Štítok úniku a signálu návratu."),
    "leverage": dict(group=_GO, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
