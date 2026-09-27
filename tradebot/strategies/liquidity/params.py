"""Popisy parametrov Liquidity pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "💧 Značenie likvidity"
_G1 = "🎯 Spúšťač a vstup"
_G2 = "🚦 Filtre a okno"
_G3 = "🛡️ Stop loss"
_G4 = "🏁 Ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7)

PARAMS: dict[str, dict[str, Any]] = {
    "liqUse5m": dict(group=_G0, title="Likvidita z 5m", inline="liqtf",
                     tooltip="Znacit likviditu zo swingov na 5m. Musi byt nasobkom TF grafu."),
    "liqUse15m": dict(group=_G0, title="15m", inline="liqtf", tooltip="Znacit likviditu zo swingov na 15m."),
    "liqUse30m": dict(group=_G0, title="30m", inline="liqtf", tooltip="Znacit likviditu zo swingov na 30m."),
    "liqUse60m": dict(group=_G0, title="1h", inline="liqtf", tooltip="Znacit likviditu zo swingov na 1h."),
    "liqUse240m": dict(group=_G0, title="4h", inline="liqtf", tooltip="Znacit likviditu zo swingov na 4h."),
    "liqPivotLen": dict(group=_G0, title="Swing: barov z kazdej strany",
                        tooltip="Vrchol/dno je swing, ked je najvyssi/najnizsi aspon o tolkoto barov dolava aj "
                                "doprava (na TF likvidity). Viac = vyznamnejsie swingy, potvrdia sa neskor."),
    "liqMinDispAtr": dict(group=_G0, title="Vyrazny swing: min. odchod (ATR)",
                          tooltip="Z vrcholu/dna musi cena odist aspon o tolko ATR (TF likvidity), inak to "
                                  "nie je likvidita, ale sum. 0 = kazdy swing."),
    "liqEqualTolAtr": dict(group=_G0, title="Rovnake vrcholy/dna: tolerancia (ATR)",
                           tooltip="Vrcholy/dna blizsie ako tolko ATR sa zlucia do jednej silnejsej urovne "
                                   "(equal highs / equal lows)."),
    "liqMaxAgeHours": dict(group=_G0, title="Platnost urovne (hodiny)",
                           tooltip="Po tolkych hodinach sa nevybrata uroven prestane sledovat."),
    "liqMinStrength": dict(group=_G0, title="Min. sila urovne",
                           tooltip="1 = kazda uroven; 2 = len zlucene rovnake vrcholy/dna (aspon dva)."),
    "tradeMode": dict(group=_G1, title="Spustac obchodu",
                      tooltip="sweep = cena zoberie likviditu a zavrie spat -> obchod proti (vyber likvidity); "
                              "breakout = zavrie za nou -> pokracovanie smeru k dalsej likvidite."),
    "tradeDirection": dict(group=_G1, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "breakBufferAtr": dict(group=_G1, title="Prerazenie: buffer (ATR)",
                           tooltip="O kolko musi byt zavretie za urovnou, aby to bolo prerazenie."),
    "sweepBars": dict(group=_G1, title="Sweep: max. barov na navrat",
                      tooltip="Ak cena urovnen prerazi a do tolkych barov zavrie spat, je to neskory sweep."),
    "entryModel": dict(group=_G1, title="Vstupny model",
                       tooltip="imbalance = IBS imbalance sviecka v smere; pinbar = pin bar; any = jedno "
                               "z nich; close = len zavretie sviecky v smere."),
    "entryOrder": dict(group=_G1, title="Typ prikazu",
                       tooltip="market = na zavreti signalnej sviecky; limit = limitka na stred signalnej sviecky."),
    "setupMaxBars": dict(group=_G1, title="Max. barov na vstupny signal",
                         tooltip="Kolko barov grafu po udalosti sa caka na vstupny model, potom sa setup zahodi."),
    "entryMaxDistAtr": dict(group=_G1, title="Vstup max. od likvidity (ATR)",
                            tooltip="Vstupny signal plati len ked je cena vstupu najviac tolko ATR od vybratej / "
                                    "prerazenej urovne - odmietnutie musi vzniknut pri likvidite, nie daleko od nej."),
    "imbMinSizeAtr": dict(group=_G1, title="Imbalance: min. medzera (ATR)",
                          tooltip="Minimalna velkost medzery imbalance sviecky v ATR grafu."),
    "pbWickPct": dict(group=_G1, title="Pin bar: min. knot (% rozsahu)",
                      tooltip="Knot proti smeru musi tvorit aspon tolko percent rozsahu sviecky."),
    "pbBodyPct": dict(group=_G1, title="Pin bar: max. telo (% rozsahu)",
                      tooltip="Telo moze tvorit najviac tolko percent rozsahu sviecky."),
    "maxTradesPerDay": dict(group=_G1, title="Max. obchodov za den", tooltip="Denny strop vstupov."),
    "cooldownBars": dict(group=_G1, title="Pauza po vstupe (bary)", tooltip="Kolko barov po vstupe sa nehlada dalsi."),
    "weekdaysOnly": dict(group=_G2, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G2, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G2, title="Casove pasmo okna", tooltip="Pasmo hodin okna a dna pre denny limit."),
    "tradeStartH": dict(group=_G2, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G2, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G2, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G2, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "slMode": dict(group=_G3, title="Kam dat stop",
                   tooltip="level = za knot sweepu / za prerazenu uroven; signal = za signalnu sviecku; "
                           "swing = za extrem poslednych N barov; atr = nasobok ATR."),
    "atrLen": dict(group=_G3, title="ATR dlzka", tooltip="Dlzka ATR (graf aj TF likvidity)."),
    "slBufferAtr": dict(group=_G3, title="Buffer stopu (ATR)", tooltip="O kolko dalej ide stop."),
    "slAtrMult": dict(group=_G3, title="SL pri rezime atr (ATR)", tooltip="Vzdialenost stopu pri slMode=atr."),
    "slLookback": dict(group=_G3, title="SL swing: barov dozadu", tooltip="Pri slMode=swing."),
    "tpMode": dict(group=_G4, title="Ciel",
                   tooltip="rr = pevny nasobok stopu; liquidity = najblizsia nevybrata likvidita v smere obchodu."),
    "rrRatio": dict(group=_G4, title="Risk:Reward (pri rr)", step=0.05, tooltip="TP = tento nasobok stopu."),
    "minRR": dict(group=_G4, title="Min. RR k likvidite", step=0.05,
                  tooltip="Pri cieli na likviditu: blizsia likvidita sa preskoci; bez ciela aspon takto daleko sa neobchoduje."),
    "maxRR": dict(group=_G4, title="Max. RR k likvidite", step=0.25,
                  tooltip="Pri cieli na likviditu: vzdialenejsi ciel sa neobchoduje. 0 = bez stropu."),
    "tpOffsetAtr": dict(group=_G4, title="Ciel pred likviditou (ATR)",
                        tooltip="TP o tolko ATR pred urovnou likvidity - aby sa vyplnil aj ked ju cena len dotkne."),
    "maxHoldBars": dict(group=_G4, title="Casovy limit obchodu (bary)", tooltip="0 = bez limitu."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showLevels": dict(group=_G6, title="Kreslit likviditu",
                       tooltip="Urovne od swingu po miesto, kde ich cena zobrala; nevybrate po koniec dat."),
    "showEvents": dict(group=_G6, title="Kreslit sweepy a prerazenia", tooltip="Stitky udalosti."),
    "tickDollarValue": dict(group=_G7, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G7, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G7, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G7, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
