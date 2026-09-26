"""Popisy parametrov Trendline Breakout pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`.
"""

from __future__ import annotations

from typing import Any

from .config import LINE_TFS

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📐 Trendovky"
_G1 = "🚀 Vstup"
_G2 = "🚦 Filtre a okno"
_G3 = "🛡️ Stop loss"
_G4 = "🎯 Ciel"
_G5 = "⏱️ Riadenie pozicie"
_G6 = "💰 Riziko"
_G7 = "🎨 Vizualizacia"
_G8 = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _G8)

PARAMS: dict[str, dict[str, Any]] = {
    # ---- 📐 Trendovky ------------------------------------------------------ #
    "lineTF": dict(
        group=_G0, title="TF trendoviek (minuty)", options=list(LINE_TFS),
        tooltip="Na akom casovom ramci sa trendovky kreslia - od 5m vyssie. Musi byt nasobkom TF "
                "grafu (graf 5m -> 5, 15, 30, 60...). Vyssi TF = menej, ale vyznamnejsich ciar.",
    ),
    "pivotLen": dict(
        group=_G0, title="Pivot: barov z kazdej strany",
        tooltip="Vrchol/dno je pivot, ked je najvyssi/najnizsi aspon o tolkoto barov dolava aj "
                "doprava (na TF trendoviek). Vacsie cislo = vyznamnejsie pivoty, ale potvrdia sa neskor.",
    ),
    "anchorMode": dict(
        group=_G0, title="Kreslit cez",
        tooltip="wick = klasicka trendovka cez knoty (high/low); body = cez tela sviecok - jeden "
                "dlhy knot ciaru neposunie.",
    ),
    "lineSlope": dict(
        group=_G0, title="Ake trendovky",
        tooltip="classic = klesajuci odpor (prerazenie nahor = long) a rastuca podpora (prerazenie "
                "nadol = short); any = aj rastuci odpor a klesajuca podpora (prerazenie kanala).",
    ),
    "maxPivots": dict(
        group=_G0, title="Kolko poslednych pivotov skusat",
        tooltip="Z kolkych poslednych vrcholov/dien sa hlada prva kotva ciary. Viac = dlhsie ciary.",
    ),
    "minTouches": dict(
        group=_G0, title="Min. pocet dotykov",
        tooltip="2 = ciara z dvoch pivotov; 3 = klasicke pravidlo tretieho dotyku - cena sa musi k "
                "ciare vratit a odraziť sa este raz, az potom sa jej prerazenie obchoduje.",
    ),
    "touchTolAtr": dict(
        group=_G0, title="Tolerancia dotyku (nasobok ATR)",
        tooltip="Ako blizko musi cena prist k ciare, aby to bol dotyk, a o kolko ju smie sviecka "
                "medzi kotvami prepichnut. V ATR trendovkoveho TF.",
    ),
    "minAnchorGap": dict(
        group=_G0, title="Min. vzdialenost kotiev (bary)",
        tooltip="Kolko barov TF trendoviek musi byt medzi dvoma pivotmi ciary - kratsie ciary su sum.",
    ),
    "lineMaxAgeBars": dict(
        group=_G0, title="Platnost ciary (bary)",
        tooltip="Kolko barov TF trendoviek po druhej kotve sa ciara este obchoduje, potom zanikne.",
    ),
    "minSlopeAtr": dict(
        group=_G0, title="Min. sklon (ATR na bar)",
        tooltip="Minimalny sklon ciary v ATR za bar TF trendoviek. Ploche ciary su skor horizontalne "
                "urovne; 0 = bez limitu.",
    ),
    "maxSlopeAtr": dict(
        group=_G0, title="Max. sklon (ATR na bar)",
        tooltip="Strmsie ciary sa neberu - prudke trendovky sa lamu rychlo a prerazenie casto "
                "prejde do bocneho pohybu. 0 = bez limitu.",
    ),
    # ---- 🚀 Vstup ------------------------------------------------------ #
    "tradeDirection": dict(
        group=_G1, title="Smer obchodov",
        tooltip="Both = obe strany; Long only = len prerazenie odporu nahor; Short only = len "
                "prerazenie podpory nadol.",
    ),
    "entryMode": dict(
        group=_G1, title="Typ vstupu",
        tooltip="close = market na zavreti sviecky za ciarou; second_close = az druhe zavretie za "
                "ciarou; retest = limitka na navrat k prerazenej ciare; retest_close = dotyk ciary "
                "a zavretie spat v smere prerazenia.",
    ),
    "breakBufferAtr": dict(
        group=_G1, title="Buffer prerazenia (nasobok ATR)",
        tooltip="O kolko musi byt zavretie za ciarou, aby to bolo prerazenie. V ATR grafu.",
    ),
    "retestMaxBars": dict(
        group=_G1, title="Max. barov na retest / druhe zavretie",
        tooltip="Kolko barov grafu po prerazeni sa caka na retest alebo potvrdenie, potom sa setup zahodi.",
    ),
    "minClosePosPct": dict(
        group=_G1, title="Min. poloha zavretia (%)",
        tooltip="Kde v rozsahu sviecky musi byt zavretie (pre long od spodku). 70 = zavretie v "
                "hornych 30 %. Odfiltruje prerazenia s dlhym knotom proti smeru.",
    ),
    "maxTradesPerDay": dict(
        group=_G1, title="Max. obchodov za den",
        tooltip="Po tomto pocte vstupov sa v dany den uz neobchoduje.",
    ),
    "cooldownBars": dict(
        group=_G1, title="Pauza po obchode (bary)",
        tooltip="Kolko barov grafu sa po vstupe alebo zlyhanom setupe nehlada dalsie prerazenie.",
    ),
    # ---- 🚦 Filtre ----------------------------------------------------- #
    "weekdaysOnly": dict(group=_G2, title="Len pondelok-piatok",
                         tooltip="Cez vikend sa neobchoduje (casove pasmo okna)."),
    "useTradeWindow": dict(group=_G2, title="Obchodne okno",
                           tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G2, title="Casove pasmo okna",
                    tooltip="Casove pasmo, v ktorom su hodiny okna a den (pre denny limit)."),
    "tradeStartH": dict(group=_G2, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G2, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G2, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G2, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    # ---- 🛡️ Stop loss -------------------------------------------------- #
    "slMode": dict(
        group=_G3, title="Kam dat stop",
        tooltip="line = za prerazenu trendovku; break_candle = za extrem prerazovacej sviecky; "
                "swing = za extrem poslednych N barov; atr = nasobok ATR od vstupu.",
    ),
    "atrLen": dict(group=_G3, title="ATR dlzka", tooltip="Dlzka ATR (graf aj TF trendoviek)."),
    "slBufferAtr": dict(group=_G3, title="Buffer stopu (nasobok ATR)",
                        tooltip="O kolko dalej za zvolenu uroven ide stop."),
    "slAtrMult": dict(group=_G3, title="SL pri rezime atr (nasobok ATR)",
                      tooltip="Vzdialenost stopu od vstupu pri slMode=atr."),
    "slLookback": dict(group=_G3, title="SL swing: barov dozadu",
                       tooltip="Z kolkych poslednych barov grafu sa berie extrem pri slMode=swing."),
    # ---- 🎯 Ciel ------------------------------------------------------- #
    "rrRatio": dict(group=_G4, title="Risk:Reward pomer", step=0.05,
                    tooltip="Take profit = tento nasobok vzdialenosti stopu."),
    # ---- ⏱️ Riadenie pozicie ------------------------------------------- #
    "enableTrailing": dict(group=_G5, title="Trailing stop",
                           tooltip="Po dosiahnuti aktivacie sa stop tahá za cenou."),
    "trailActivationR": dict(group=_G5, title="Trailing: aktivacia (R)",
                             tooltip="Pri akom zisku (v nasobkoch rizika) sa trailing zapne."),
    "trailOffsetR": dict(group=_G5, title="Trailing: odstup (R)",
                         tooltip="Ako daleko za cenou ide stop (v nasobkoch rizika)."),
    "maxHoldBars": dict(group=_G5, title="Casovy limit obchodu (bary)",
                        tooltip="Po tolkych baroch grafu sa obchod zavrie za trh. 0 = bez limitu."),
    "closeAtWindowEnd": dict(group=_G5, title="Zavriet na konci okna",
                             tooltip="Na konci obchodneho okna zavriet otvorenu poziciu."),
    # ---- 💰 Riziko ----------------------------------------------------- #
    "riskDollar": dict(group=_G6, title="Riziko na obchod ($)",
                       tooltip="Velkost pozicie sa pocita tak, aby strata na stope bola tato suma."),
    # ---- 🎨 Vizualizacia ----------------------------------------------- #
    "showLines": dict(group=_G7, title="Kreslit trendovky",
                      tooltip="Kreslit odpor a podporu, ktore stratégia obchoduje."),
    "showPivots": dict(group=_G7, title="Kreslit pivoty",
                       tooltip="Oznacit vrcholy a dna, z ktorych sa ciary kreslia."),
    # ---- 🧩 Rozšírenia portu ------------------------------------------- #
    "tickDollarValue": dict(group=_G8, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G8, title="Pine sizing",
                             tooltip="Dosloveny Pine vzorec velkosti pozicie - len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G8, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (v % z ceny). 0 = vypnute."),
    "leverage": dict(group=_G8, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
