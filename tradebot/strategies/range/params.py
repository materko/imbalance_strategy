"""Popisy parametrov Range Breakout pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🔍 Detekcia rangu"
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
    # ---- 🔍 Detekcia rangu -------------------------------------------- #
    "lookbackBars": dict(
        group=_G0, title="Dlzka okna (bary)",
        tooltip="V kolkych poslednych baroch sa hlada konsolidacia. Kratsie okno = viac a mensich "
                "rangov, dlhsie = menej ale vyznamnejsich. Bezne 10-20.",
    ),
    "boundaryMode": dict(
        group=_G0, title="Z coho brat hranice",
        tooltip="close = najvyssi/najnizsi ZAVER v okne (odolnejsie voci jednemu dlhemu knotu); "
                "extreme = high/low (klasicke, ale jeden knot vie range rozsirit a znehodnotit).",
    ),
    "minWidthAtr": dict(
        group=_G0, title="Min. sirka rangu (nasobok ATR)",
        tooltip="Pod tuto sirku je to sum, nie konsolidacia - prerazenie by nemalo kam ist. "
                "V ATR, aby prah platil na kazdom trhu rovnako.",
    ),
    "maxWidthAtr": dict(
        group=_G0, title="Max. sirka rangu (nasobok ATR)",
        tooltip="Nad tuto sirku uz nejde o tesnu konsolidaciu, ale o siroky rozhadzany pohyb - "
                "prerazenia z neho su podla merani najmenej spolahlive. Bezne 1,5-2,5.",
    ),
    "maxRangeAgeBars": dict(
        group=_G0, title="Max. vek rangu (bary)",
        tooltip="Ak sa range do tolkoto barov od najdenia neprerazi, zahodi sa a hlada sa nanovo. "
                "Brani tomu, aby sa obchodovalo prerazenie davno neplatnej urovne.",
    ),
    "cooldownBars": dict(
        group=_G0, title="Pauza po obchode (bary)",
        tooltip="Kolko barov sa po vstupe alebo po zlyhanom prerazeni nehlada novy range. "
                "Bez pauzy stratégia casto otvori ten isty setup znova.",
    ),
    # ---- 🚀 Vstup ------------------------------------------------------ #
    "tradeDirection": dict(
        group=_G1, title="Smer obchodov",
        tooltip="Both = obe strany; Long only / Short only obmedzi stratégiu na jednu stranu.",
    ),
    "entryMode": dict(
        group=_G1, title="Typ vstupu",
        tooltip="close = vstup hned na zavreti prerazovacej sviecky (chyti aj rychle pohyby, ale "
                "aj falosne prerazenia); retest = limitka na navrat k prerazenej hranici (lepsia "
                "cena, cast pohybov utecie); continuation = po retestte sa este caka na potvrdzujuci "
                "zaver v smere prerazenia (najprisnejsie, najmenej obchodov).",
    ),
    "breakBufferAtr": dict(
        group=_G1, title="Buffer prerazenia (nasobok ATR)",
        tooltip="O kolko musi zaver presiahnut hranicu, aby sa prerazenie pocitalo. Filtruje "
                "tesne prerazenia o jeden tick, ktore sa hned vratia.",
    ),
    "requireSecondClose": dict(
        group=_G1, title="Vyzadovat druhy potvrdzujuci zaver",
        tooltip="Zapnute: prerazenie plati az ked za hranicou zavru DVE sviecky po sebe. Zvysi "
                "spolahlivost, ale zhorsi vstupnu cenu a ubere obchody.",
    ),
    "retestMaxBars": dict(
        group=_G1, title="Retest: max barov na navrat",
        tooltip="Do kolkych barov od prerazenia sa musi cena vratit na hranicu. Po uplynuti sa "
                "setup zahodi. Tyka sa vstupu retest aj continuation.",
    ),
    "confirmMaxBars": dict(
        group=_G1, title="Continuation: max barov na potvrdenie",
        tooltip="Po dotyku hranice (retest) tolkoto barov na potvrdzujuci zaver v smere prerazenia. "
                "Plati len pri vstupe continuation.",
    ),
    "maxTradesPerDay": dict(
        group=_G1, title="Max obchodov za den",
        tooltip="Strop na pocet vstupov za jeden kalendarny den v pasme obchodneho okna.",
    ),
    "minClosePosPct": dict(
        group=_G1, title="Min. poloha zavretia v sviecke (%)",
        tooltip="Ako vysoko v ramci prerazovacej sviecky musi byt jej zaver (pri long; pri short "
                "zrkadlovo). 50 % = zaver aspon v polovici sviecky. Filtruje prerazenia, ktore "
                "skoncili dlhym knotom proti smeru.",
    ),
    # ---- 🚦 Filtre a okno ---------------------------------------------- #
    "weekdaysOnly": dict(
        group=_G2, title="Obchoduj len Pondelok-Piatok",
        tooltip="Vypne vikendy - podstatne pre krypto, na CFD je vikend aj tak zatvoreny.",
    ),
    "useTradeWindow": dict(
        group=_G2, title="Obmedzit na obchodne okno",
        tooltip="Vypnute: range sa obchoduje kedykolvek (24h). Zapnute: vstupy len v okne nizsie - "
                "napr. len pocas newyorskej seansy.",
    ),
    "tradeTZ": dict(
        group=_G2, title="Casove pasmo okna",
        tooltip="Pasmo, v ktorom su hodiny okna zadane (napr. America/New_York, Europe/London).",
    ),
    "tradeStartH": dict(group=_G2, title="Okno: zaciatok (H)", tooltip="Hodina zaciatku obchodneho okna."),
    "tradeStartM": dict(group=_G2, title="Okno: zaciatok (M)", tooltip="Minuta zaciatku obchodneho okna."),
    "tradeEndH": dict(group=_G2, title="Okno: koniec (H)", tooltip="Hodina konca obchodneho okna."),
    "tradeEndM": dict(group=_G2, title="Okno: koniec (M)", tooltip="Minuta konca obchodneho okna."),
    # ---- 🛡️ Stop loss --------------------------------------------------- #
    "slMode": dict(
        group=_G3, title="Umiestnenie SL",
        tooltip="opposite = opacna hrana rangu (najbezpecnejsie, ale najsirsi stop); mid = stred "
                "rangu; range_pct = do rangu o nastavene % jeho vysky; atr = nasobok ATR od vstupu; "
                "break_candle = za extrem prerazovacej sviecky (najtesnejsie).",
    ),
    "slRangePct": dict(
        group=_G3, title="SL: hlbka do rangu (% vysky)",
        tooltip="Plati len pri umiestneni SL range_pct. 50 % je to iste ako mid, 100 % ako opposite.",
    ),
    "atrLen": dict(group=_G3, title="ATR dlzka", tooltip="Pocet barov pre ATR, z ktoreho sa "
                                                         "pocitaju vsetky prahy v jednotke atr."),
    "slAtrMult": dict(group=_G3, title="SL vzdialenost (nasobok ATR)",
                      tooltip="Plati len pri umiestneni SL atr."),
    "slBufferAtr": dict(group=_G3, title="Buffer za SL uroven (nasobok ATR)",
                        tooltip="Kolko sa prida za vypocitanu uroven SL, aby ho nezobral bezny sum."),
    # ---- 🎯 Ciel -------------------------------------------------------- #
    "tpMode": dict(
        group=_G4, title="Vypocet ciela",
        tooltip="rr = nasobok vzdialenosti SL; measured = vyska rangu premietnuta za prerazenie "
                "(klasicky measured move); atr = nasobok ATR.",
    ),
    "rrRatio": dict(group=_G4, title="Risk:Reward pomer",
                    tooltip="Plati pri cieli rr: kolkonasobok vzdialenosti SL je take profit."),
    "measuredMult": dict(group=_G4, title="Measured move: nasobok vysky rangu",
                         tooltip="Plati pri cieli measured. 1,0 = presne vyska rangu za prerazenim."),
    "tpAtrMult": dict(group=_G4, title="TP vzdialenost (nasobok ATR)", tooltip="Plati pri cieli atr."),
    # ---- ⏱️ Riadenie pozicie -------------------------------------------- #
    "enableTrailing": dict(group=_G5, title="Zapnut trailing stop",
                           tooltip="Po dosiahnuti aktivacie posuva SL za cenou."),
    "trailActivationR": dict(group=_G5, title="Aktivacia trailingu (R-nasobok)",
                             tooltip="Pri akom zisku v nasobkoch rizika sa trailing zapne."),
    "trailOffsetR": dict(group=_G5, title="Trailing vzdialenost (R-nasobok)",
                         tooltip="Ako daleko za cenou trailing SL ide."),
    "maxHoldBars": dict(group=_G5, title="Max. dlzka obchodu (bary)",
                        tooltip="0 = vypnute. Inak sa pozicia po tolkoto baroch zatvori za trh - "
                                "range breakout, ktory sa do tej doby nepohol, uz obvykle nepojde."),
    "closeAtWindowEnd": dict(group=_G5, title="Zatvor poziciu na konci okna",
                             tooltip="Plati len so zapnutym obchodnym oknom. Zabrani drzaniu pozicie "
                                     "cez noc."),
    # ---- 💰 Riziko ------------------------------------------------------ #
    "riskDollar": dict(group=_G6, title="Riziko na obchod ($)",
                       tooltip="Z neho a zo vzdialenosti SL sa pocita velkost pozicie. 0 = 1 kus."),
    # ---- 🎨 Vizualizacia ------------------------------------------------ #
    "showRange": dict(group=_G7, title="Kreslit box rangu", tooltip="Box konsolidacie na grafe."),
    "showLevels": dict(group=_G7, title="Kreslit hranice rangu",
                       tooltip="Vodorovne ciary hornej a dolnej hranice."),
    # ---- 🧩 Rozsirenia portu -------------------------------------------- #
    "tickDollarValue": dict(group=_G8, title="Hodnota ticku ($)",
                            tooltip="CFD a futures ju potrebuju na risk-based sizing."),
    "leverage": dict(group=_G8, title="Paka",
                     tooltip="Paka vo Freqtrade futures. Nemeni edge, len umozni otvorit poziciu, "
                             "ktora by sa inak na ucet nezmestila."),
}
