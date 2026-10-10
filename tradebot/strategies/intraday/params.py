"""Popisy parametrov INTRADAY 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_filter import entry_filter_params

__all__ = ["GROUPS", "PARAMS"]

_GB = "🧭 Daily bias a likvidita"
_GZ = "📦 SD zóny 1H → 15m → 5m"
_GE = "🎯 Vstup"
_GX = "🛡️ Stop a cieľ"
_GR = "💰 Veľkosť"
_GD = "🎨 Vizualizácia"
_GP = "🧩 Rozšírenia portu"
_GF = "🧾 Spoločné filtre vstupu"

GROUPS: tuple[str, ...] = (_GB, _GZ, _GE, _GX, _GR, _GD, _GP, _GF)

PARAMS: dict[str, dict[str, Any]] = {
    "biasMode": dict(group=_GB, title="Daily bias", options=["ema", "close2", "off"],
                     tooltip="ema = včerajšie zavretie RTH nad / pod EMA denných zavretí; close2 = včera vs predvčerom; off = oba smery."),
    "biasEmaLen": dict(group=_GB, title="EMA denných zavretí", tooltip="Dĺžka EMA pre bias ema (dni)."),
    "liqMode": dict(group=_GB, title="Likvidita v protismere", options=["zone", "sweep", "off"],
                    tooltip="zone = zóna vstupu leží pri / pod PDL (long) resp. pri / nad PDH (short) — cena pri ceste do zóny zoberie likviditu; "
                            "sweep = PDL / PDH už bolo dnes zobraté; off = bez podmienky."),
    "liqTolAtr": dict(group=_GB, title="Tolerancia zóny k PDL / PDH (ATR grafu)", step=0.25,
                      tooltip="Pri zone: proximal smie byť nad PDL (pod PDH) najviac o toľko ATR."),
    "entryTF": dict(group=_GZ, title="TF zóny vstupu", options=[60, 15, 5],
                    tooltip="5 = 5m zóna v 15m zóne v 1H zóne (celá smernica); 15 = 15m v 1H; 60 = rovno 1H zóna."),
    "baseMaxBars": dict(group=_GZ, title="Max. sviečok bázy", tooltip="Báza = 1 až N sviečok s malými telami."),
    "baseMaxBodyPct": dict(group=_GZ, title="Báza: max. telo (% rozsahu)", tooltip="Sviečka bázy má telo najviac toľko % rozsahu."),
    "impulseMinBodyPct": dict(group=_GZ, title="Impulz: min. telo (% rozsahu)", tooltip="Prvá sviečka odchodu."),
    "impulseMinBodyAtr": dict(group=_GZ, title="Impulz: min. telo (ATR TF)", step=0.1, tooltip="Telo impulzu aspoň toľko ATR toho TF."),
    "legOutMinAtr": dict(group=_GZ, title="Silný odchod (ATR TF)", step=0.1,
                         tooltip="Zóna vznikne, keď cena zavrie za bázou aspoň o toľko ATR toho TF (smernica: silný impulz)."),
    "legOutMaxBars": dict(group=_GZ, title="Odchod do (sviečok)", tooltip="Do koľkých sviečok TF musí odchod dobehnúť."),
    "zoneAge60": dict(group=_GZ, title="Životnosť 1H zóny (h)", tooltip="Po toľkých hodinách zóna vyprší."),
    "zoneAge15": dict(group=_GZ, title="Životnosť 15m zóny (h)", tooltip="Po toľkých hodinách zóna vyprší."),
    "zoneAge5": dict(group=_GZ, title="Životnosť 5m zóny (h)", tooltip="Po toľkých hodinách zóna vyprší."),
    "entryModel": dict(group=_GE, title="Vstup", options=["touch", "reject"],
                       tooltip="touch = limitka na hranu zóny (dotyk); reject = po dotyku sviečka zavrie späť mimo zóny → market."),
    "entryDepthPct": dict(group=_GE, title="Limitka do hĺbky zóny (%)", tooltip="0 = na hrane (proximal), 50 = stred zóny."),
    "startH": dict(group=_GE, title="Okno od: hodina (NY)", inline="w1", tooltip="Začiatok vstupov."),
    "startM": dict(group=_GE, title="minúta", inline="w1", tooltip=""),
    "endH": dict(group=_GE, title="Okno do: hodina (NY)", inline="w2", tooltip="Koniec vstupov."),
    "endM": dict(group=_GE, title="minúta", inline="w2", tooltip=""),
    "maxTradesPerDay": dict(group=_GE, title="Max. obchodov za deň", tooltip="Denný strop vstupov."),
    "tradeDirection": dict(group=_GE, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "weekdaysOnly": dict(group=_GE, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "slBufferAtr": dict(group=_GX, title="Rezerva stopu za zónou (ATR grafu)", step=0.05, tooltip="Stop = distal zóny ± rezerva."),
    "tpMode": dict(group=_GX, title="Cieľ", options=["rr", "liquidity"],
                   tooltip="rr = násobok stopu; liquidity = opačná likvidita predošlého dňa (PDH pri longu)."),
    "rrRatio": dict(group=_GX, title="Cieľ (násobok stopu)", step=0.25, tooltip="Pri cieli rr."),
    "minRR": dict(group=_GX, title="Min. RR pri cieli na likviditu", step=0.25, tooltip="Bližší cieľ = bez obchodu; 0 = vypnuté."),
    "atrLen": dict(group=_GX, title="ATR dĺžka", tooltip="ATR grafu aj TF zón."),
    "useExitTime": dict(group=_GX, title="Zavrieť v čase", tooltip="Pravidlá testovania: vypnuté."),
    "exitH": dict(group=_GX, title="Hodina", inline="ex", tooltip="NY."),
    "exitM": dict(group=_GX, title="Minúta", inline="ex", tooltip=""),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "showZones": dict(group=_GD, title="Kresliť zóny", tooltip="1H modré, 15m fialové, 5m oranžové — len vnorené zóny."),
    "showLiquidity": dict(group=_GD, title="Kresliť PDH / PDL", tooltip="High a low predošlého RTH dňa."),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_filter_params(_GF))
