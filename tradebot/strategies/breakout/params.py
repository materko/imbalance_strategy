"""Popisy parametrov Breakoutu pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`
(`CONSTRAINTS` a defaulty dataclass), zoznamy hodnôt enumov sa dopĺňajú z `ENUM_FIELDS`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕐 Seansa"
_G1 = "🚀 Vstup"
_G2 = "🚦 Filtre"
_G3 = "🛡️ Stop loss"
_G4 = "🎯 Ciel"
_G5 = "⏱️ Riadenie pozicie"
_G6 = "💰 Riziko"
_G7 = "🎨 Vizualizacia"
_G8 = "🧩 Rozšírenia portu"

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _G8)

PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🕐 Seansa ---------------------------------------------------- #
    "sessionStartH": dict(
        group=_G0, title="Otvorenie seansy (H)",
        tooltip="Hodina otvorenia New York cash seansy v pasme America/New_York. Standardne 9:30 NY, "
                "co je 15:30 stredoeurospkeho casu - pasmo rieši prechod na letny cas samo, preto sa "
                "cas zadava v New Yorku a nie v SEC.",
    ),
    "sessionStartM": dict(
        group=_G0, title="Otvorenie seansy (M)",
        tooltip="Minuta otvorenia seansy. Prva sviecka od tohto casu je otvaracia.",
    ),
    "openingMinutes": dict(
        group=_G0, title="Dlzka otvaracej sviecky (min)",
        tooltip="Kolko minut trva otvaracia sviecka, ktorej high a low su jedine dve urovne "
                "stratégie. Berie sa z informativneho TF, nie z barov grafu: 5 sa dvomi ani tromi "
                "nedeli, takze na 3m grafe by z barov vysla sviecka 9:30-9:36. Takto vidi 1m, 2m aj "
                "3m graf presne tu istu hranicu.",
    ),
    "sessionEndH": dict(
        group=_G0, title="Koniec seansy (H)",
        tooltip="Hodina, po ktorej sa uz nevstupuje a otvorena pozicia sa zatvara (ak je zapnute "
                "zatvaranie na konci seansy). Standardne 15:55 NY, tesne pred zvonom.",
    ),
    "sessionEndM": dict(
        group=_G0, title="Koniec seansy (M)",
        tooltip="Minuta konca seansy.",
    ),
    "weekdaysOnly": dict(
        group=_G0, title="Len pracovne dni",
        tooltip="Vypne sobotu a nedelu. Na indexoch a futures je to bez ucinku (trh aj tak stoji), "
                "na krypte to odfiltruje vikendy s inym charakterom obchodovania.",
    ),
    # ---- 🚀 Vstup ------------------------------------------------------ #
    "tradeDirection": dict(
        group=_G1, title="Smer obchodov",
        tooltip="Both = prerazenie hore aj dole; Long only = len zavretie nad high otvaracej "
                "sviecky; Short only = len zavretie pod jej low.",
    ),
    "orderType": dict(
        group=_G1, title="Typ prikazu",
        tooltip="market = vstup hned na zavreti prerazovacej sviecky; vstupi sa vzdy, ale za horsiu "
                "cenu. limit = limitka spat na prerazenu hranicu (retest); lepsia cena a kratsi stop, "
                "ale cast prerazeni sa nevrati a obchod nevznikne. Signal je v oboch ten isty, lisi "
                "sa len plnenie - preto sa daju porovnat jeden proti druhemu.",
    ),
    "breakBufferAtr": dict(
        group=_G1, title="Rezerva prerazenia (nasobok ATR)", step=0.05,
        tooltip="O kolko musi close prekonat hranicu, aby sa prerazenie ratalo. 0 = staci akykolvek "
                "close za nou. Jednotka ATR, aby prah znamenal to iste na kazdom trhu.",
    ),
    "limitValidMinutes": dict(
        group=_G1, title="Platnost limitky (min)",
        tooltip="Ako dlho ceka limitka na retest hranice. Po uplynuti sa zrusi a v ten den sa uz "
                "nevstupuje (pokus sa zapocital do stropu obchodov). Plati len pri type prikazu limit.",
    ),
    "entryWindowMinutes": dict(
        group=_G1, title="Okno na vstup od otvorenia (min)",
        tooltip="Ako dlho po otvoreni seansy sa este smie vstupit. 90 = prerazenie po 11:00 NY sa "
                "ignoruje. 0 = bez obmedzenia, az do konca seansy.",
    ),
    "maxTradesPerDay": dict(
        group=_G1, title="Max. pokusov o vstup za den",
        tooltip="Strop na pocet zadanych vstupnych prikazov za den. Pocita sa pokus, nie vyplneny "
                "obchod: ci sa limitka vrati k hranici, engine na bare zadania nevie.",
    ),
    "minClosePosPct": dict(
        group=_G1, title="Min. poloha close v sviecke (%)",
        tooltip="Kde v rozpati prerazovacej sviecky musi byt jej close: 0 % = na minime, 100 % = na "
                "maxime (pri shorte zrkadlovo). Odfiltruje prerazenia zavrete dlhym knotom proti smeru. "
                "0 = vypnute.",
    ),
    # ---- 🚦 Filtre ----------------------------------------------------- #
    "minRangePct": dict(
        group=_G2, title="Min. sirka otvaracej sviecky (% ceny)", step=0.05,
        tooltip="Prilis uzka otvaracia sviecka znamena, ze sa trh na otvoreni nepohol - jej hranice "
                "prerazi kazdy sum. 0 = vypnute.",
    ),
    "maxRangePct": dict(
        group=_G2, title="Max. sirka otvaracej sviecky (% ceny)", step=0.05,
        tooltip="Prilis siroka otvaracia sviecka (sprava, gap) da stop tak daleko, ze ciel v RR je "
                "nedosiahnutelny. Nad tento prah sa den preskoci.",
    ),
    "useVolumeFilter": dict(
        group=_G2, title="Filter objemu",
        tooltip="Zapne poziadavku, aby mala prerazovacia sviecka nadpriemerny objem.",
    ),
    "volSmaLen": dict(
        group=_G2, title="Dlzka SMA objemu (bary)",
        tooltip="Z kolkych predchadzajucich barov grafu sa pocita priemerny objem.",
    ),
    "volMultiplier": dict(
        group=_G2, title="Nasobok priemerneho objemu", step=0.1,
        tooltip="Objem prerazovacej sviecky musi byt aspon tolkokrat vacsi nez priemer.",
    ),
    # ---- 🛡️ Stop loss --------------------------------------------------- #
    "atrLen": dict(
        group=_G3, title="ATR dlzka",
        tooltip="Dlzka ATR (Wilder) na baroch grafu. ATR sa tu pouziva len ako jednotka pre rezervy, "
                "samotny stop ide vzdy pod/nad otvaraciu sviecku.",
    ),
    "slBufferAtr": dict(
        group=_G3, title="Rezerva pod sviecku (nasobok ATR)", step=0.05,
        tooltip="O kolko nizsie nez low otvaracej sviecky (pri shorte vyssie nez jej high) ide stop. "
                "0 = presne na uroven sviecky.",
    ),
    # ---- 🎯 Ciel -------------------------------------------------------- #
    "rrRatio": dict(
        group=_G4, title="Risk:Reward pomer", step=0.5,
        tooltip="Take profit = rrRatio × vzdialenost stopu. 1 = 1:1, 1.5 = 1:1,5, 2 = 1:2 a tak dalej.",
    ),
    # ---- ⏱️ Riadenie pozicie ------------------------------------------- #
    "enableTrailing": dict(
        group=_G5, title="Trailing stop",
        tooltip="Po dosiahnuti aktivacie posuva stop za cenou. Obmedzi velke vyhry, ale zachrani cast "
                "obchodov, ktore by sa vratili na stop.",
    ),
    "trailActivationR": dict(
        group=_G5, title="Aktivacia trailingu (R)", step=0.1,
        tooltip="Pri akom zisku v nasobkoch rizika sa trailing zapne.",
    ),
    "trailOffsetR": dict(
        group=_G5, title="Odstup trailingu (R)", step=0.1,
        tooltip="Ako daleko za cenou stop ide, v nasobkoch rizika.",
    ),
    "closeAtSessionEnd": dict(
        group=_G5, title="Zatvorit poziciu na konci seansy",
        tooltip="Otvorena pozicia sa na konci seansy zatvori trhovo. Vypnute = drzi sa, kym nepride "
                "stop alebo ciel - cez noc a cez gap.",
    ),
    # ---- 💰 Riziko ------------------------------------------------------ #
    "riskDollar": dict(
        group=_G6, title="Riziko na obchod ($)", step=10.0,
        tooltip="Velkost pozicie = riziko / vzdialenost stopu. Vysledok sa tak da prepocitat na iny "
                "ucet. 0 = 1 kontrakt.",
    ),
    # ---- 🎨 Vizualizacia ------------------------------------------------ #
    "showRange": dict(
        group=_G7, title="Kreslit otvaraciu sviecku",
        tooltip="Box cez telo a knoty otvaracej sviecky - to, na co sa cela strategia pozera.",
    ),
    "showLevels": dict(
        group=_G7, title="Kreslit hranice (high a low)",
        tooltip="Dve vodorovne ciary z high a low otvaracej sviecky cez zvysok dna.",
    ),
    # ---- 🧩 Rozsirenia portu -------------------------------------------- #
    "tickDollarValue": dict(
        group=_G8, title="Hodnota ticku ($)",
        tooltip="Kolko dolarov je pohyb o jeden tick na jeden kontrakt. CFD a futures nastroje to "
                "potrebuju na vypocet velkosti pozicie z rizika.",
    ),
    "legacyPineSizing": dict(
        group=_G8, title="Pine sizing (1 kontrakt, ako TradingView)",
        tooltip="Doslovny Pine vzorec velkosti pozicie vratane int() a max(1, ...). Zapnut LEN na "
                "porovnanie s TradingView; pri qty < 1 sa limit rizika ticho neuplatni. Vyzaduje "
                "zadany tickDollarValue.",
    ),
    "minSlDistance": dict(
        group=_G8, title="Min. vzdialenost SL od vstupu",
        tooltip="Obchod s tesnejsim SL sa preskoci. Poplatok je percento z nominalu a zisk rastie s R, "
                "takze tesne stopy maju najhorsi pomer edge k poplatku. 0 = vypnute. Odporucana "
                "jednotka pct (napr. 0,20 % ceny).",
    ),
    "leverage": dict(
        group=_G8, title="Páka",
        tooltip="Paka vo Freqtrade futures. Nemeni edge, len umozni otvorit poziciu z risk-based "
                "sizingu, ktora by sa inak na ucet nezmestila.",
    ),
}
