"""Popisy parametrov ORB pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`
(`CONSTRAINTS` a defaulty dataclass), zoznamy hodnôt enumov sa dopĺňajú z `ENUM_FIELDS`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕐 Seansy"
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

#: `pole configu -> {group, title, tooltip}`.
PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🕐 Seansy ---------------------------------------------------- #
    "sessionMode": dict(
        group=_G0, title="Ktore seansy obchodovat",
        tooltip="both = New York aj Londyn, kazda ma vlastny range aj vlastny obchod; ny = len New York"
                "open; london = len Londyn open.",
    ),
    "nyStartH": dict(
        group=_G0, title="New York: otvorenie (H)",
        tooltip="Hodina otvorenia New York cash seansy v pasme America/New_York. Standardne 9:30.",
    ),
    "nyStartM": dict(
        group=_G0, title="New York: otvorenie (M)",
        tooltip="Minuta otvorenia New York seansy.",
    ),
    "nyRangeMinutes": dict(
        group=_G0, title="New York: dlzka rangu",
        tooltip="Kolko minut od otvorenia NY tvori opening range. 15 = viac signalov a viac falosnych;"
                "30 = vyvazene; 60 = najmenej obchodov, ale najcistejsie.",
    ),
    "nyEndH": dict(
        group=_G0, title="New York: koniec seansy (H)",
        tooltip="Hodina, kedy sa NY pozicie zatvaraju a prestava sa vstupovat.",
    ),
    "nyEndM": dict(
        group=_G0, title="New York: koniec seansy (M)",
        tooltip="Minuta konca NY seansy.",
    ),
    "lonStartH": dict(
        group=_G0, title="Londyn: otvorenie (H)",
        tooltip="Hodina otvorenia londynskej seansy v pasme Europe/London. Standardne 8:00.",
    ),
    "lonStartM": dict(
        group=_G0, title="Londyn: otvorenie (M)",
        tooltip="Minuta otvorenia londynskej seansy.",
    ),
    "lonRangeMinutes": dict(
        group=_G0, title="Londyn: dlzka rangu",
        tooltip="Kolko minut od otvorenia Londyna tvori opening range.",
    ),
    "lonEndH": dict(
        group=_G0, title="Londyn: koniec seansy (H)",
        tooltip="Hodina, kedy sa londynske pozicie zatvaraju a prestava sa vstupovat.",
    ),
    "lonEndM": dict(
        group=_G0, title="Londyn: koniec seansy (M)",
        tooltip="Minuta konca londynskej seansy.",
    ),
    # ---- 🚀 Vstup ----------------------------------------------------- #
    "tradeDirection": dict(
        group=_G1, title="Smer obchodov",
        tooltip="Ktore prerazenia sa obchoduju. Na indexoch s dlhodobym rastom byva Long only silnejsi.",
    ),
    "entryMode": dict(
        group=_G1, title="Typ vstupu",
        tooltip="close = vstup na zavreti sviecky za hranicou (vyvazene); retest = caka sa na navrat na"
                "prerazenu hranicu a vstup limitkou (lepsi RR, cast pohybov utecie); stop = agresivny"
                "stop order priamo na hranici.",
    ),
    "breakBufferAtr": dict(
        group=_G1, title="Buffer prerazenia (nasobok ATR)", step=0.01,
        tooltip="O kolko musi cena prekrocit hranicu, aby sa to ratalo ako prerazenie. Filtruje dotyky"
                "hranice na tick.",
    ),
    "retestMaxBars": dict(
        group=_G1, title="Retest: max barov na navrat",
        tooltip="Pri type vstupu retest: kolko barov po prerazeni sa caka na navrat k hranici. Potom sa"
                "setup zahadzuje.",
    ),
    "entryWindowMinutes": dict(
        group=_G1, title="Vstup najneskor do (minuty od otvorenia)",
        tooltip="Plati zvlast pre kazdu seansu, od jej vlastneho otvorenia. Prerazenia neskor v seanse"
                "vyrazne zaostavaju. 0 = bez obmedzenia.",
    ),
    "maxTradesPerDay": dict(
        group=_G1, title="Max obchodov na seansu a den",
        tooltip="Kolko pokusov o prerazenie sa smie spravit v jednej seanse za jeden den. Pri oboch"
                "zapnutych seansach je denne maximum dvojnasobok.",
    ),
    # ---- 🚦 Filtre ---------------------------------------------------- #
    "minRangePct": dict(
        group=_G2, title="Min. sirka rangu (% ceny)", step=0.05,
        tooltip="Prilis uzky range = dominuju falosne prerazenia. Merania odporucaju aspon 0,3 % na"
                "indexoch.",
    ),
    "maxRangePct": dict(
        group=_G2, title="Max. sirka rangu (% ceny)", step=0.1,
        tooltip="Prilis siroky range = stop je daleko a RR sa kazi.",
    ),
    "useVolumeFilter": dict(
        group=_G2, title="Zapnut volume filter",
        tooltip="Vyzaduje, aby prerazovacia sviecka mala nadpriemerny objem. Na CFD datach moze byt"
                "objem nespolahlivy.",
    ),
    "volSmaLen": dict(
        group=_G2, title="Volume: priemer za N sviecok",
        tooltip="Dlzka priemeru objemu, s ktorym sa prerazovacia sviecka porovnava.",
    ),
    "volMultiplier": dict(
        group=_G2, title="Volume: min. nasobok priemeru", step=0.1,
        tooltip="Objem prerazovacej sviecky musi byt aspon tolkokrat nad priemerom.",
    ),
    "minClosePosPct": dict(
        group=_G2, title="Min. poloha zavretia v sviecke (%)",
        tooltip="Pri LONG musi sviecka zavriet aspon v tejto hornej casti svojho rozsahu (pri SHORT v"
                "dolnej). Odfiltruje prerazenia s dlhym odmietacim knotom.",
    ),
    "weekdaysOnly": dict(
        group=_G2, title="Obchoduj len Pondelok-Piatok",
        tooltip="Vypne vikendove bary.",
    ),
    # ---- 🛡️ Stop loss ------------------------------------------------ #
    "slMode": dict(
        group=_G3, title="Umiestnenie SL",
        tooltip="opposite = na opacnu hranu rangu (= 100 % vysky rangu); mid = na stred rangu (= 50 %);"
                "range_pct = do rangu o nastavene percento jeho vysky, meria sa od prerazenej hranice;"
                "atr = nasobok ATR od vstupu; break_candle = za low/high prerazovacej sviecky"
                "(najtesnejsi).",
    ),
    "slRangePct": dict(
        group=_G3, title="SL: hlbka do rangu (% vysky rangu)", step=5,
        tooltip="Pouzije sa pri umiestneni SL nastavenom na range_pct. Meria sa od prerazenej hranice"
                "smerom do rangu: 25 % = tesny stop tesne pod hranicou, 50 % = stred rangu, 100 % ="
                "opacna hrana. Nad 100 % ide stop az za range.",
    ),
    "atrLen": dict(
        group=_G3, title="ATR dlzka",
        tooltip="Dlzka ATR (Wilder) pre vsetky ATR jednotky.",
    ),
    "slAtrMult": dict(
        group=_G3, title="SL vzdialenost (nasobok ATR)", step=0.1,
        tooltip="Pouzije sa len ked je umiestnenie SL nastavene na atr.",
    ),
    "slBufferAtr": dict(
        group=_G3, title="Buffer za SL uroven (nasobok ATR)", step=0.05,
        tooltip="Kolko sa prida za vypocitanu SL uroven, aby stop prezil bezny knot.",
    ),
    # ---- 🎯 Ciel ------------------------------------------------------ #
    "tpMode": dict(
        group=_G4, title="Vypocet ciela",
        tooltip="rr = nasobok vzdialenosti SL (riadi ho Risk:Reward pomer nizsie); measured = vyska"
                "rangu premietnuta za prerazenie (klasicky measured move); atr = nasobok ATR.",
    ),
    "rrRatio": dict(
        group=_G4, title="Risk:Reward pomer", step=0.1,
        tooltip="Take profit = rrRatio × vzdialenost SL. Pouzije sa pri vypocte ciela rr.",
    ),
    "measuredMult": dict(
        group=_G4, title="Measured move: nasobok vysky rangu", step=0.1,
        tooltip="Ciel = miesto prerazenia -/+ (vyska rangu × tento nasobok). Pouzije sa pri vypocte"
                "ciela measured.",
    ),
    "tpAtrMult": dict(
        group=_G4, title="TP vzdialenost (nasobok ATR)", step=0.1,
        tooltip="Pouzije sa pri vypocte ciela atr.",
    ),
    # ---- ⏱️ Riadenie pozicie ----------------------------------------- #
    "enableTrailing": dict(
        group=_G5, title="Zapnut trailing stop",
        tooltip="Po dosiahnuti aktivacnej urovne sa stop tiahne za cenou.",
    ),
    "trailActivationR": dict(
        group=_G5, title="Aktivacia trailingu (R-nasobok)", step=0.1,
        tooltip="Pri akom zisku v nasobkoch rizika sa trailing zapne.",
    ),
    "trailOffsetR": dict(
        group=_G5, title="Trailing vzdialenost (R-nasobok)", step=0.1,
        tooltip="Ako daleko za cenou sa stop tiahne, v nasobkoch rizika.",
    ),
    "closeAtSessionEnd": dict(
        group=_G5, title="Zatvor poziciu na konci seansy",
        tooltip="Intradenne: pozicia sa nedrzi cez noc. Zatvara ju koniec tej seansy, v ktorej vznikla.",
    ),
    # ---- 💰 Riziko ---------------------------------------------------- #
    "riskDollar": dict(
        group=_G6, title="Riziko na obchod ($)", step=10,
        tooltip="Velkost pozicie = riziko / vzdialenost SL. 0 = 1 kontrakt.",
    ),
    # ---- 🎨 Vizualizacia ---------------------------------------------- #
    "showRange": dict(
        group=_G7, title="Kreslit opening range",
        tooltip="Zapne box opening rangu pre kazdu zapnutu seansu.",
    ),
    "showLevels": dict(
        group=_G7, title="Kreslit hranice rangu",
        tooltip="Zapne predlzene ciary high a low rangu cez zvysok seansy.",
    ),
    # ---- 🧩 Rozšírenia portu ------------------------------------ #
    "tickDollarValue": dict(
        group=_G8, title="Hodnota ticku ($)",
        tooltip="Koľko dolárov je pohyb o jeden tick na jeden kontrakt. CFD a futures nástroje "
                "to potrebujú na výpočet veľkosti pozície z rizika.",
    ),
    "leverage": dict(
        group=_G8, title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based "
                "sizingu, ktorá by sa inak na účet nezmestila.",
    ),
}
