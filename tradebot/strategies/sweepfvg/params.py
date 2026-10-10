"""Popisy parametrov SWEEP FVG 1.0 pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_filter import entry_filter_params

__all__ = ["GROUPS", "PARAMS"]

_GL = "💧 Likvidita a jej výber"
_GS = "🔀 CHoCH / BOS"
_GE = "🟪 FVG a vstup"
_GX = "🛡️ Stop a cieľ"
_GR = "💰 Veľkosť"
_GD = "🎨 Vizualizácia"
_GP = "🧩 Rozšírenia portu"
_GF = "🧾 Spoločné filtre vstupu"

GROUPS: tuple[str, ...] = (_GL, _GS, _GE, _GX, _GR, _GD, _GP, _GF)

PARAMS: dict[str, dict[str, Any]] = {
    "liqUse5m": dict(group=_GL, title="Likvidita z 5m", inline="liqtf",
                     tooltip="Značiť likviditu zo swingov na 5m. Musí byť násobkom TF grafu."),
    "liqUse15m": dict(group=_GL, title="15m", inline="liqtf", tooltip="Značiť likviditu zo swingov na 15m."),
    "liqUse30m": dict(group=_GL, title="30m", inline="liqtf", tooltip="Značiť likviditu zo swingov na 30m."),
    "liqUse60m": dict(group=_GL, title="1h", inline="liqtf", tooltip="Značiť likviditu zo swingov na 1h."),
    "liqUse240m": dict(group=_GL, title="4h", inline="liqtf", tooltip="Značiť likviditu zo swingov na 4h."),
    "liqPivotLen": dict(group=_GL, title="Swing likvidity: barov z každej strany",
                        tooltip="Vrchol / dno je swing, keď je najvyšší / najnižší aspoň o toľkoto barov doľava aj doprava (na TF likvidity)."),
    "liqMinDispAtr": dict(group=_GL, title="Výrazný swing: min. odchod (ATR)", step=0.1,
                          tooltip="Z vrcholu / dna musí cena odísť aspoň o toľko ATR (TF likvidity), inak to nie je likvidita."),
    "liqEqualTolAtr": dict(group=_GL, title="Rovnaké vrcholy / dná: tolerancia (ATR)", step=0.05,
                           tooltip="Vrcholy / dná bližšie ako toľko ATR sa zlúčia do jednej silnejšej úrovne."),
    "liqMaxAgeHours": dict(group=_GL, title="Platnosť úrovne (hodiny)", tooltip="Po toľkých hodinách sa nevybratá úroveň prestane sledovať."),
    "liqMinStrength": dict(group=_GL, title="Min. sila úrovne", tooltip="1 = každá úroveň; 2 = len rovnaké vrcholy / dná (aspoň dva)."),
    "sweepReclaim": dict(group=_GL, title="Výber: zavrieť späť",
                         tooltip="Vypnuté = výber je každé prerazenie úrovne (aj zavretím za ňou). Zapnuté = sviečka výberu musí zavrieť späť pred úroveň."),
    "structPivotLen": dict(group=_GS, title="Swing grafu: barov z každej strany",
                           tooltip="Swingy grafu, za ktoré musí cena po výbere prejsť (CHoCH / BOS). Menej = skorší zlom."),
    "breakBy": dict(group=_GS, title="Zlom", options=["close", "wick"],
                    tooltip="close = sviečka zavrie za swingom; wick = stačí knôt."),
    "breakType": dict(group=_GS, title="Typ zlomu", options=["any", "choch", "bos"],
                      tooltip="any = CHoCH aj BOS; choch = len zlom proti doterajšiemu smeru štruktúry; bos = len v jeho smere."),
    "breakMaxBars": dict(group=_GS, title="Zlom do (barov po výbere)", tooltip="Ak zlom nepríde do toľkých barov, výber sa zahodí."),
    "fvgMinAtr": dict(group=_GE, title="Signifikantný FVG: min. medzera (ATR)", step=0.05,
                      tooltip="Medzera medzi 1. a 3. sviečkou aspoň toľko ATR grafu."),
    "fvgPick": dict(group=_GE, title="Ktorý FVG", options=["nearest", "largest", "first"],
                    tooltip="nearest = najbližší k cene; largest = najväčší; first = prvý po výbere (pri extréme)."),
    "fvgWaitBars": dict(group=_GE, title="FVG aj po zlome (barov)",
                        tooltip="FVG smie vzniknúť ešte toľko barov po zlome (sviečka zlomu býva stredom FVG)."),
    "entryLevel": dict(group=_GE, title="Vstup", options=["edge", "mid"],
                       tooltip="edge = limitka na okraji FVG, ku ktorému sa cena vracia; mid = na strede FVG."),
    "entryMaxBars": dict(group=_GE, title="Čakať na vstup (barov)", tooltip="Koľko barov po zlome čaká limitka na vyplnenie."),
    "maxTradesPerDay": dict(group=_GE, title="Max. obchodov za deň", tooltip="Denný strop vstupov."),
    "tradeDirection": dict(group=_GE, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "weekdaysOnly": dict(group=_GE, title="Len pondelok–piatok", tooltip="Cez víkend sa neobchoduje."),
    "useTradeWindow": dict(group=_GE, title="Obchodné okno (NY)", tooltip="Limitky len v zadanom čase New York."),
    "startH": dict(group=_GE, title="Okno od: hodina", inline="w1", tooltip="Začiatok vstupov (NY)."),
    "startM": dict(group=_GE, title="minúta", inline="w1", tooltip=""),
    "endH": dict(group=_GE, title="Okno do: hodina", inline="w2", tooltip="Koniec vstupov (NY)."),
    "endM": dict(group=_GE, title="minúta", inline="w2", tooltip=""),
    "slBufferAtr": dict(group=_GX, title="Rezerva stopu za výberom (ATR)", step=0.05, tooltip="SL = extrém výberu likvidity ± rezerva."),
    "maxSlAtr": dict(group=_GX, title="Max. stop (ATR)", step=0.5, tooltip="Širší stop = bez obchodu. 0 = vypnuté."),
    "tpMode": dict(group=_GX, title="Cieľ", options=["rr", "points", "liquidity"],
                   tooltip="rr = násobok stopu; points = pevne v bodoch; liquidity = najbližšia nevybratá likvidita v smere obchodu."),
    "rrRatio": dict(group=_GX, title="Cieľ (násobok stopu)", step=0.25, tooltip="Pri cieli rr."),
    "tpPoints": dict(group=_GX, title="Cieľ v bodoch", tooltip="Pri cieli points."),
    "minRR": dict(group=_GX, title="Min. RR k likvidite", step=0.25, tooltip="Pri cieli liquidity: bližšia likvidita sa preskočí."),
    "atrLen": dict(group=_GX, title="ATR dĺžka", tooltip="ATR grafu aj TF likvidity."),
    "useExitTime": dict(group=_GX, title="Zavrieť v čase", tooltip="Pravidlá testovania: vypnuté."),
    "exitH": dict(group=_GX, title="Hodina (NY)", inline="ex", tooltip=""),
    "exitM": dict(group=_GX, title="Minúta", inline="ex", tooltip=""),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_GR, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "showLevels": dict(group=_GD, title="Kresliť likviditu", tooltip="Úrovne od swingu po miesto, kde ich cena zobrala."),
    "showStructure": dict(group=_GD, title="Kresliť výber a CHoCH / BOS", tooltip="Štítok výberu a čiara zlomu."),
    "showFvg": dict(group=_GD, title="Kresliť FVG", tooltip="Vybraný FVG, na ktorého okraji je limitka."),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_filter_params(_GF))
