"""Popisy parametrov Silver Bullet 1.0 pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params

__all__ = ["GROUPS", "PARAMS"]

_GW = "🕙 Okno Silver Bullet"
_GL = "💧 Likvidita a sweep"
_GE = "🟪 FVG a vstup"
_GX = "🛡️ Stop a cieľ"
_GR = "💰 Veľkosť"
_GD = "🎨 Vizualizácia"
_GP = "🧩 Rozšírenia portu"
_GF = "🧾 Spoločné filtre vstupu"

GROUPS: tuple[str, ...] = (_GW, _GL, _GE, _GX, _GR, _GD, _GP, _GF)

PARAMS: dict[str, dict[str, Any]] = {
    "sbStartH": dict(group=_GW, title="Začiatok okna (hod., NY)", inline="sbs",
                     tooltip="Sweep, FVG aj vstup musia prísť v okne. ICT Silver Bullet: 10:00 New York."),
    "sbStartM": dict(group=_GW, title="min", inline="sbs", tooltip="Minúty začiatku okna."),
    "sbEndH": dict(group=_GW, title="Koniec okna (hod., NY)", inline="sbe",
                   tooltip="Nevyplnená limitka sa na konci okna zruší. ICT: 11:00 New York."),
    "sbEndM": dict(group=_GW, title="min", inline="sbe", tooltip="Minúty konca okna."),
    "liqFromH": dict(group=_GL, title="Likvidita od (hod., NY)", inline="lqf",
                     tooltip="Odkedy sa berú skoršie vrcholy a dná dňa. 8:00 = od otvorenia newyorského rána."),
    "liqFromM": dict(group=_GL, title="min", inline="lqf", tooltip="Minúty začiatku zberu likvidity."),
    "useRangeHL": dict(group=_GL, title="High / low pred oknom",
                       tooltip="Najvyšší vrchol a najnižšie dno úseku od „Likvidita od“ po začiatok okna sú likvidita."),
    "useSwings": dict(group=_GL, title="Swingy grafu",
                      tooltip="Vrcholy a dná grafu od „Likvidita od“ (aj v okne pred sweepom) sú likvidita."),
    "liqPivotLen": dict(group=_GL, title="Swing: barov z každej strany",
                        tooltip="Vrchol / dno je swing, keď je najvyšší / najnižší o toľko barov doľava aj doprava."),
    "sweepReclaim": dict(group=_GL, title="Sweep: zavretie späť za úroveň",
                         tooltip="Zapnuté = sviečka musí úroveň prerazit knôtom a zavrieť späť; vypnuté = stačí knôt (ICT)."),
    "fvgMinAtr": dict(group=_GE, title="FVG: min. medzera (ATR)", step=0.05,
                      tooltip="Medzera medzi 1. a 3. sviečkou aspoň toľko ATR."),
    "fvgMaxBars": dict(group=_GE, title="FVG do (barov po extréme sweepu)",
                       tooltip="Prudký pohyb s FVG musí prísť najviac toľko barov po extréme sweepu."),
    "requireMss": dict(group=_GE, title="Aj zlom štruktúry (MSS)",
                       tooltip="Navyše zavretie za posledný swing grafu pred extrémom sweepu (market structure shift)."),
    "structPivotLen": dict(group=_GE, title="MSS: swing barov z každej strany", tooltip="Swing grafu pre zlom štruktúry."),
    "entryLevel": dict(group=_GE, title="Limitka na FVG",
                       tooltip="edge = okraj FVG, ku ktorému sa cena vracia; mid = stred FVG (consequent encroachment)."),
    "entryType": dict(group=_GE, title="Typ vstupu",
                      tooltip="limit = limitka na FVG, platí do konca okna (ICT); market = na zavretí sviečky, ktorá FVG "
                              "vytvorila (dá sa potvrdiť IBS imbalance / pin bar)."),
    "maxTradesPerDay": dict(group=_GE, title="Max. obchodov za deň", tooltip="Silver Bullet: jeden obchod v okne."),
    "tradeDirection": dict(group=_GE, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "weekdaysOnly": dict(group=_GE, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "slBufferAtr": dict(group=_GX, title="SL: rezerva za extrém sweepu (ATR)", step=0.05,
                        tooltip="Stop je za extrémom sweepu o toľko ATR."),
    "maxSlAtr": dict(group=_GX, title="SL: najviac (ATR), 0 = bez stropu", step=0.25,
                     tooltip="Príliš veľký sweep (stop) sa neobchoduje."),
    "tpMode": dict(group=_GX, title="Cieľ",
                   tooltip="liquidity = najbližšia protiľahlá likvidita (skorší vrchol / dno, ICT); rr = násobok stopu."),
    "rrRatio": dict(group=_GX, title="Cieľ RR", step=0.25, tooltip="Cieľ = vstup ± RR × stop."),
    "minRR": dict(group=_GX, title="Cieľ na likvidite: aspoň (R)", step=0.25,
                  tooltip="Bližšia likvidita sa preskočí; keď žiadna nie je, obchod sa nerobí."),
    "atrLen": dict(group=_GX, title="ATR: dĺžka", tooltip="ATR grafu pre FVG a stop."),
    "useExitTime": dict(group=_GX, title="Výstup v čase",
                        tooltip="Nie je súčasť ICT pravidiel — default vypnuté (len stop a cieľ)."),
    "exitH": dict(group=_GX, title="Výstup (hod., NY)", inline="ex", tooltip="Hodina výstupu."),
    "exitM": dict(group=_GX, title="min", inline="ex", tooltip="Minúty výstupu."),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov",
                     tooltip="Zapnuté = qty kontraktov; vypnuté = veľkosť z rizika v $ k stopu."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "showWindow": dict(group=_GD, title="Kresliť okno", tooltip="Box okna 10–11 NY."),
    "showLevels": dict(group=_GD, title="Kresliť likviditu a sweep", tooltip="Úrovne likvidity a štítok sweepu."),
    "showFvg": dict(group=_GD, title="Kresliť FVG", tooltip="FVG, na ktorom je vstup."),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_confirm_params(_GF))
PARAMS.update(entry_filter_params(_GF))
