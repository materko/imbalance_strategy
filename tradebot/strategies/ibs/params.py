"""Popisy parametrov pre formulár webapp — pri stratégii, nie v Pine.

Zdroj pravdy pre to, **ako sa parameter volá po ľudsky a čo robí**. Rozsahy a defaulty
sem nepatria: tie sú v `config.py` (`CONSTRAINTS` a defaulty dataclass) a formulár si ich
vyzdvihne odtiaľ, takže sa nemá ako rozísť s tým, čo config prijme. Zoznam hodnôt enumu
sa dopĺňa sám z `ENUM_FIELDS`.

Prečo pri stratégii a nie v Pine: Pine skript vzniká len na vyžiadanie (aby sa stratégia
dala pozrieť na TradingView) a formulár na ňom nesmie závisieť.

Tento súbor vznikol jednorazovým prevodom z imbalance_strategy_FULL.pine; odvtedy sa mení tu.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (
    "🎯 Obchodovanie",
    "⚙️ Základné nastavenia",
    "📦 SD Zony",
    "🌏 Session 1 (Azia)",
    "📘 Session 2",
    "📙 Session 3",
    "📈 Market Structure",
    "📏 Support/Resistance",
    "💧 Likvidita (Sweep)",
    "🌊 Elliott Waves",
    "🎨 Vizualizacia",
    "🔧 Pokročilé (časovanie vstupu, SL)",
    "💰 Veľkosť pozície a riziko",
    "🔗 PickMyTrade",)

#: `pole configu -> {group, title, tooltip, [step], [options], [inline]}`.
PARAMS: dict[str, dict[str, Any]] = {
    "enableImbEntry": dict(group="🎯 Obchodovanie", title="IMB entry (imbalance/gap)",
        tooltip="Povodny model - hlada imbalance/gap vnutri zony, caka na exit, potvrdenie "
                "zavretim za telom, a navrat/retest na presnu cenu gapu (postupny, viacbarovy "
                "proces s viacerymi kontrolnymi fazami).",
    ),
    "enablePinBarEntry": dict(group="🎯 Obchodovanie", title="Pin Bar entry",
        tooltip="Ked v zone vznikne pin bar v spravnom smere, po jeho zatvoreni sa rovno vytvori "
                "order (entry=close pin baru, SL=opacny wick pin baru + buffer, TP podla RR "
                "pomeru) - vsetko v jednom bare, bez cakania na potvrdenie.",
    ),
    "enableEngulfingEntry": dict(group="🎯 Obchodovanie", title="Engulfing entry",
        tooltip="Ked v zone vznikne podstatne vacsia sviecka ako okolite (jej celkovy rozsah "
                "high-low je aspon X-nasobkom priemerneho rozsahu poslednych N sviecok - vid "
                "vstupy nizsie), po jej zatvoreni sa rovno vytvori order (entry=close, SL=opacny "
                "extrem tejto sviecky + buffer, TP podla RR pomeru) - vsetko v jednom bare, bez "
                "cakania na potvrdenie.",
    ),
    "pbWickToBodyRatio": dict(group="🎯 Obchodovanie", title="Pin Bar: Min. pomer knôt/telo", step=0.1,
        tooltip="Knot (v smere vstupu) musi byt aspon X-nasobkom tela sviecky. Klasicka definicia "
                "pin baru = 2.0.",
    ),
    "pbBodyPositionPct": dict(
        group="🎯 Obchodovanie", title="Pin Bar: Max. poloha tela v rozsahu (%)", step=1.0,
        tooltip="Telo sviecky (aj s opacnym knotom) musi byt v tejto % casti CELKOVEHO rozsahu "
                "sviecky, pocitane od spravneho okraja. Klasicka definicia = 33%.",
    ),
    "pbMinRangePoints": dict(
        group="🎯 Obchodovanie", title="Pin Bar: Min. celkový rozsah sviečky (body)", step=0.5,
        tooltip="Filter proti sumu - pin bar musi mat aspon tento celkovy rozsah (high-low). 0 = "
                "vypnute.",
    ),
    "engMinRangePoints": dict(
        group="🎯 Obchodovanie", title="Engulfing: Min. celkový rozsah sviečky (body)", step=0.5,
        tooltip="Filter proti sumu - engulfing (potvrdzujuca) sviecka musi mat aspon tento celkovy "
                "rozsah (high-low). 0 = vypnute.",
    ),
    "engSizeAvgLen": dict(group="🎯 Obchodovanie", title="Engulfing: Dĺžka priemeru rozsahu (bary)",
        tooltip="Pocet predchadzajucich sviecok, z ktorych sa pocita priemerny rozsah (high-low) "
                "pre porovnanie velkosti - viz 'Engulfing: Nasobok priemerneho rozsahu' nizsie.",
    ),
    "engSizeMultiplier": dict(
        group="🎯 Obchodovanie", title="Engulfing: Násobok priemerného rozsahu", step=0.1,
        tooltip="Aktualna sviecka musi mat celkovy rozsah (high-low) aspon tolkokrat vacsi, ako je "
                "priemerny rozsah poslednych 'Engulfing: Dlzka priemeru rozsahu' sviecok - teda "
                "vyrazny 'outlier' oproti okoliu. Vyssie cislo = prisnejsie, hlada len naozaj "
                "extremne velke sviecky.",
    ),
    "engTouchWindowBars": dict(group="🎯 Obchodovanie", title="Engulfing: Max. barov po dotyku zóny",
        tooltip="Po prvom dotyku zony ma Engulfing model tolkoto barov 'trpezlivosti' na to, aby "
                "sa vytvoril - pocas tohto okna sa zona NEINVALIDUJE ani ked cena uz cez nu celu "
                "prejde (na rozdiel od Pin Bar/IMB modelu). Az po uplynuti tohto okna bez najdenia "
                "patternu plati normalna invalidacia (cena prejde cez opacnu stranu zony).",
    ),
    "pbEngOrderType": dict(group="🎯 Obchodovanie", title="Pin Bar/Engulfing: Typ príkazu",
        tooltip="Plati LEN pre Pin Bar entry a Engulfing entry (IMB entry vzdy posiela Limit na "
                "cene gapu, nemenne). Limit = order caka na navrat ceny presne na close signalnej "
                "sviecky (ako doteraz). Market = order sa posle hned na najblizsom moznom vyplneni "
                "(bez cakania na navrat ceny) - SL/TP zostavaju vypocitane z teoretickej entry "
                "ceny (close signalnej sviecky), takze pri Market sa skutocny RR moze mierne "
                "odchylit kvoli skiznu/gapu. Tento prepinac meni AJ 'order_type' pole v JSON-e, "
                "ktory sa posiela do PickMyTrade (viz sekcia PickMyTrade) - takze sa zmeni aj typ "
                "prikazu na realnom brokerovi, nielen v TradingView simulacii.",
    ),
    "enableTrailing": dict(group="🎯 Obchodovanie", title="Zapnúť trailing stop",
        tooltip="Klasicky trailing stop - po dosiahnuti zisku vo vyske 'Aktivacia trailingu' sa SL "
                "zacne automaticky posuvat za cenou. Vypnute (default) = ziadna zmena povodneho "
                "spravania (pevny SL/TP podla RR pomeru po celu dobu obchodu). DOLEZITE: tento "
                "prepinac riadi trailing AJ v TradingView simulacii (cez strategy.exit), AJ na "
                "realnom brokerovi cez PickMyTrade (cez JSON polia "
                "trail/trail_trigger/trail_stop/trail_freq v alert_message) - viz pmtMsg() a "
                "sekcia PickMyTrade nizsie.",
    ),
    "trailActivationR": dict(group="🎯 Obchodovanie", title="Aktivácia trailingu (R-násobok rizika)", step=0.1,
        tooltip="Trailing sa aktivuje az ked je obchod v zisku rovnom tolkoto-nasobku povodneho "
                "rizika (vzdialenosti entry-SL danej pozicie). Napr. 1.0 = aktivuje sa presne ked "
                "zisk dosiahne 1R (rovna sa povodnemu riziku). Pouziva sa rovnako pre TradingView "
                "simulaciu aj pre PickMyTrade JSON (prepocitane na cenove body namiesto ticky).",
    ),
    "trailOffsetR": dict(group="🎯 Obchodovanie", title="Trailing vzdialenosť (R-násobok rizika)", step=0.05,
        tooltip="Po aktivacii trailing stop sleduje najlepsiu dosiahnutu cenu vo vzdialenosti "
                "tolkoto-nasobku povodneho rizika. Nizsie cislo = tesnejsie sledovanie ceny (skor "
                "zamkne zisk, ale aj vacsia sanca vypadnut z obchodu pri malom protipohybe pred "
                "TP). Pouziva sa rovnako pre TradingView simulaciu aj pre PickMyTrade JSON.",
    ),
    "weekdaysOnly": dict(group="⚙️ Základné nastavenia", title="Obchoduj len Pondelok-Piatok",
        tooltip="Ak zapnute, strategia obchoduje len Pondelok az Piatok - soboty a nedele su "
                "preskocene bez ohladu na nastavenia seansii nizsie.",
    ),
    "enableTrading": dict(
        group="⚙️ Základné nastavenia", title="Zapnut obchodovanie (strategia posiela ordre)",
        tooltip="Ak vypnute, strategia nikdy neposle ziadny order a nepocita obchody do "
                "dashboardu/trade logu. Detekcia SD zon a gapov bezi dalej nezavisle (podla "
                "nastavenia nizsie).",
    ),
    "enableZoneDetection": dict(group="🎯 Obchodovanie", title="Zapnut detekciu SD zon",
        tooltip="Ak vypnute, prestanu sa tvorit NOVE SD zony (uz existujuce dobehnu do konca). "
                "Nezavisle od toho, ci je zapnute obchodovanie.",
    ),
    "enableGapDetection": dict(group="📦 SD Zony", title="Zapnut hladanie gapu vnutri zony",
        tooltip="Ak vypnute, zona nikdy nenajde gap na vstup (zostane cakat), teda sa z nej nikdy "
                "nevytvori order. Nezavisle od detekcie zon aj od obchodovania.",
    ),
    "enableSrTrading": dict(
        group="🎯 Obchodovanie", title="Obchoduj z S/R úrovní (rovnaký mechanizmus ako SD zóny)",
        tooltip="Ked S/R uroven dosiahne 'Min. pocet dotykov' (viz sekcia Support/Resistance), "
                "vytvori sa z nej OBCHODOVATELNA zona - rovnakym sposobom ako pri SD zone "
                "(hladanie gapu, potvrdenie, limit order, SL/TP cez RR pomer). Smer (LONG/SHORT) "
                "sa urcuje podla aktualnej polohy ceny voci urovni - support (cena nad urovnou) = "
                "LONG zona, resistance (cena pod urovnou) = SHORT zona.",
    ),
    "enableLqTrading": dict(group="🎯 Obchodovanie", title="Obchoduj z likviditných zón (sweep)",
        tooltip="Ked sa potvrdi liquidity sweep (viz sekcia Likvidita), vytvori sa z neho "
                "OBCHODOVATELNA zona v smere PROTI sweepu (fade - presne ako sweep uz teraz "
                "funguje) - rovnakym sposobom ako pri SD zone (hladanie gapu, potvrdenie, limit "
                "order, SL/TP cez RR pomer). Zona = rozsah medzi swept urovnou a najdalsim bodom "
                "prepichnutia (wick).",
    ),
    "closeAtSessionEnd": dict(group="⚙️ Základné nastavenia", title="Zatvor vsetky pozicie na konci session",
        tooltip="Ak zapnute, na konci KAZDEJ obchodnej seansy (nie len konca dna) sa automaticky "
                "zatvoria vsetky otvorene pozicie a zrusia cakajuce ordery a nepotvrdene zony, aby "
                "nepresahovali do dalsej seansy.",
    ),
    "sess1On": dict(group="🌏 Session 1 (Azia)", title="Zapnúť", inline="s1on",
        tooltip="Zapne/vypne celu Session 1 (Azia) - ked je vypnuta, v tomto casovom okne sa "
                "nekresli ziadna nova SD zona ani sa neposiela ziadny obchod.",
    ),
    "sess1TZ": dict(group="🌏 Session 1 (Azia)", title="Časové pásmo", inline="s1on",
        tooltip="Casove pasmo, v ktorom su definovane vsetky casy Session 1 nizsie (IANA timezone, "
                "napr. Europe/Prague).",
    ),
    "sess1ZoneStartH": dict(group="🌏 Session 1 (Azia)", title="SD zona zaciatok (H)", inline="s1z",
        tooltip="Zaciatok casoveho okna (hodina), v ktorom sa pre Session 1 hladaju/kreslia nove "
                "SD zony.",
    ),
    "sess1ZoneStartM": dict(group="🌏 Session 1 (Azia)", title="M", inline="s1z",
        tooltip="Zaciatok okna pre SD zony Session 1 - minuty.",
    ),
    "sess1ZoneEndH": dict(group="🌏 Session 1 (Azia)", title="SD zona koniec (H)", inline="s1ze",
        tooltip="Koniec casoveho okna (hodina), v ktorom sa pre Session 1 hladaju/kreslia nove SD "
                "zony.",
    ),
    "sess1ZoneEndM": dict(group="🌏 Session 1 (Azia)", title="M", inline="s1ze",
        tooltip="Koniec okna pre SD zony Session 1 - minuty.",
    ),
    "sess1TradeStartH": dict(group="🌏 Session 1 (Azia)", title="Trade zaciatok (H)", inline="s1t",
        tooltip="Zaciatok obchodneho okna (hodina) pre Session 1 - az od tohto casu moze strategia "
                "realne poslat order. Moze byt iny ako okno pre zony.",
    ),
    "sess1TradeStartM": dict(group="🌏 Session 1 (Azia)", title="M", inline="s1t",
        tooltip="Zaciatok obchodneho okna Session 1 - minuty.",
    ),
    "sess1TradeEndH": dict(group="🌏 Session 1 (Azia)", title="Trade koniec (H)", inline="s1te",
        tooltip="Koniec obchodneho okna (hodina) pre Session 1 - po tomto case sa uz nove ordery "
                "pre tuto seansu neposielaju.",
    ),
    "sess1TradeEndM": dict(group="🌏 Session 1 (Azia)", title="M", inline="s1te",
        tooltip="Koniec obchodneho okna Session 1 - minuty.",
    ),
    "sess2On": dict(group="📘 Session 2", title="Zapnúť", inline="s2on",
        tooltip="Zapne/vypne celu Session 2 - ked je vypnuta, v tomto casovom okne sa nekresli "
                "ziadna nova SD zona ani sa neposiela ziadny obchod.",
    ),
    "sess2TZ": dict(group="📘 Session 2", title="Časové pásmo", inline="s2on",
        tooltip="Casove pasmo, v ktorom su definovane vsetky casy Session 2 nizsie (IANA timezone, "
                "napr. America/New_York).",
    ),
    "sess2ZoneStartH": dict(group="📘 Session 2", title="SD zona zaciatok (H)", inline="s2z",
        tooltip="Zaciatok casoveho okna (hodina), v ktorom sa pre Session 2 hladaju/kreslia nove "
                "SD zony.",
    ),
    "sess2ZoneStartM": dict(group="📘 Session 2", title="M", inline="s2z",
        tooltip="Zaciatok okna pre SD zony Session 2 - minuty.",
    ),
    "sess2ZoneEndH": dict(group="📘 Session 2", title="SD zona koniec (H)", inline="s2ze",
        tooltip="Koniec casoveho okna (hodina), v ktorom sa pre Session 2 hladaju/kreslia nove SD "
                "zony.",
    ),
    "sess2ZoneEndM": dict(group="📘 Session 2", title="M", inline="s2ze",
        tooltip="Koniec okna pre SD zony Session 2 - minuty.",
    ),
    "sess2TradeStartH": dict(group="📘 Session 2", title="Trade zaciatok (H)", inline="s2t",
        tooltip="Zaciatok obchodneho okna (hodina) pre Session 2 - az od tohto casu moze strategia "
                "realne poslat order. Moze byt iny ako okno pre zony.",
    ),
    "sess2TradeStartM": dict(group="📘 Session 2", title="M", inline="s2t",
        tooltip="Zaciatok obchodneho okna Session 2 - minuty.",
    ),
    "sess2TradeEndH": dict(group="📘 Session 2", title="Trade koniec (H)", inline="s2te",
        tooltip="Koniec obchodneho okna (hodina) pre Session 2 - po tomto case sa uz nove ordery "
                "pre tuto seansu neposielaju.",
    ),
    "sess2TradeEndM": dict(group="📘 Session 2", title="M", inline="s2te",
        tooltip="Koniec obchodneho okna Session 2 - minuty.",
    ),
    "sess3On": dict(group="📙 Session 3", title="Zapnúť", inline="s3on",
        tooltip="Zapne/vypne celu Session 3 - ked je vypnuta, v tomto casovom okne sa nekresli "
                "ziadna nova SD zona ani sa neposiela ziadny obchod.",
    ),
    "sess3TZ": dict(group="📙 Session 3", title="Časové pásmo", inline="s3on",
        tooltip="Casove pasmo, v ktorom su definovane vsetky casy Session 3 nizsie (IANA timezone, "
                "napr. Europe/London).",
    ),
    "sess3ZoneStartH": dict(group="📙 Session 3", title="SD zona zaciatok (H)", inline="s3z",
        tooltip="Zaciatok casoveho okna (hodina), v ktorom sa pre Session 3 hladaju/kreslia nove "
                "SD zony.",
    ),
    "sess3ZoneStartM": dict(group="📙 Session 3", title="M", inline="s3z",
        tooltip="Zaciatok okna pre SD zony Session 3 - minuty.",
    ),
    "sess3ZoneEndH": dict(group="📙 Session 3", title="SD zona koniec (H)", inline="s3ze",
        tooltip="Koniec casoveho okna (hodina), v ktorom sa pre Session 3 hladaju/kreslia nove SD "
                "zony.",
    ),
    "sess3ZoneEndM": dict(group="📙 Session 3", title="M", inline="s3ze",
        tooltip="Koniec okna pre SD zony Session 3 - minuty.",
    ),
    "sess3TradeStartH": dict(group="📙 Session 3", title="Trade zaciatok (H)", inline="s3t",
        tooltip="Zaciatok obchodneho okna (hodina) pre Session 3 - az od tohto casu moze strategia "
                "realne poslat order. Moze byt iny ako okno pre zony.",
    ),
    "sess3TradeStartM": dict(group="📙 Session 3", title="M", inline="s3t",
        tooltip="Zaciatok obchodneho okna Session 3 - minuty.",
    ),
    "sess3TradeEndH": dict(group="📙 Session 3", title="Trade koniec (H)", inline="s3te",
        tooltip="Koniec obchodneho okna (hodina) pre Session 3 - po tomto case sa uz nove ordery "
                "pre tuto seansu neposielaju.",
    ),
    "sess3TradeEndM": dict(group="📙 Session 3", title="M", inline="s3te",
        tooltip="Koniec obchodneho okna Session 3 - minuty.",
    ),
    "zoneDetectionTF": dict(
        group="📦 SD Zony", title="SD zona - detekcny TF (z akeho TF sa hlada pattern)", options=["1", "3", "5", "15", "30", "45", "60", "120", "180", "240", "D"],
        tooltip="Na tomto timeframe sa hlada 4-sviečkový pattern (imbalance / 3 rovnake sviece), z "
                "ktoreho sa vytvara SD zona. Predtym bolo napevno 5 minut, teraz si vies vybrat aj "
                "15, 60 (1H) atd. - vyssi TF = menej, ale vyznamnejsie zony.",
    ),
    "zoneValidHours": dict(group="📦 SD Zony", title="Platnost zony (hodiny)",
        tooltip="Ako dlho (v hodinach od vzniku) zostava zona - SD, S/R aj likviditna - aktivna a "
                "obchodovatelna, kym sa automaticky nezneplatni.",
    ),
    "maxSdZones": dict(group="📦 SD Zony", title="Max SD zon",
        tooltip="Maximalny pocet sucasne sledovanych zon (spolu zo vsetkych troch zdrojov - SD, "
                "S/R, likvidita) - po prekroceni sa najstarsia zona aj s jej boxami odstrani, aby "
                "graf a pamat nepretazili.",
    ),
    "snapMode": dict(group="📦 SD Zony", title="Snap casu zony na TF grid",
        tooltip="Ako sa zaokruhluje casovy zaciatok SD zony na najblizsiu hranicu aktualneho TF "
                "grafu - Floor=nadol, Ceil=nahor, Round=najblizsie, Off=bez zaokruhlenia.",
    ),
    "invalidateOnFill": dict(group="📦 SD Zony", title="Invaliduj zonu pri vyplneni orderu",
        tooltip="Ak je zaskrtnute, SD zona sa vizualne uzavrie ked sa order vyplni.",
    ),
    "useVolumeFilter": dict(group="📦 SD Zony", title="Zapnúť volume filter (SD zóny)",
        tooltip="Zapne vyhodnocovanie volume pri vzniku SD zony (priemer 3 impulznych sviecok, "
                "ktore zonu tvoria) aj pri jej entry potvrdeni (aktualna sviecka pri umiestneni "
                "orderu). Silne (volume-potvrdene) zony sa VZDY vizualne oznacia ZELENOU farbou "
                "namiesto bezneho cervena/modra Demand/Supply - bez ohladu na to, ci nizsie zapnes "
                "aj blokovanie. Netyka sa S/R ani Likviditnych zon.",
    ),
    "volumeFilterBlockTrading": dict(group="📦 SD Zony", title="Aj blokovať slabé (nízky volume) zóny",
        tooltip="Ak je zapnute (aj vyssie 'Zapnut volume filter'), zony/entry s nedostatocnym "
                "volume sa VOBEC nevytvoria/neposlu - rovnaky mechanizmus ako ostatne filtre "
                "(napr. BOS/CHoCH). Ak vypnute (default), vsetky SD zony aj nadalej vznikaju a "
                "obchoduju sa ako doteraz - volume filter len farebne oznaci silne/slabe, "
                "rozhodnutie necha na tebe (napr. pre discretionary pouzitie).",
    ),
    "volSmaLen": dict(group="📦 SD Zony", title="Volume: priemer za N sviečok",
        tooltip="Pocet sviecok, z ktorych sa pocita priemerny (SMA) volume - pri vzniku zony na "
                "detekcnom TF (zoneDetectionTF), pri entry potvrdeni na TF grafu.",
    ),
    "volMultiplier": dict(group="📦 SD Zony", title="Volume: min. násobok priemeru pre 'silnú' zónu", step=0.1,
        tooltip="Volume musi byt aspon tolkokrat vyssi ako priemer (SMA), aby sa zona/entry "
                "povazovali za volume-potvrdene ('silne').",
    ),
    "showMarketStructure": dict(group="📈 Market Structure", title="Zobraz strukturu trhu (BOS/CHoCH)",
        tooltip="Zapne/vypne kreslenie BOS/CHoCH ciar a HH/HL/LH/LL popiskov na grafe. Nema priamy "
                "vplyv na obchodovanie - to riadi az 'BOS/CHoCH filter' (ak je zapnuty), ktory "
                "funguje aj ked je tato vizualizacia vypnuta.",
    ),
    "structureSwingLen": dict(group="📈 Market Structure", title="Swing lookback (barov na kazdu stranu)",
        tooltip="Kolko barov na obe strany musi byt nizsie/vyssie, aby sa bod potvrdil ako swing "
                "high/low. Vyssie cislo = menej, ale vyznamnejsie swingy (a vecsie oneskorenie "
                "potvrdenia).",
    ),
    "useStructureFilter": dict(
        group="📈 Market Structure", title="Obchoduj len v smere struktury (BOS/CHoCH filter)",
        tooltip="Ak zapnute, LONG order sa umiestni len ked je aktualna struktura trhu bullish "
                "(posledny break bol smerom hore) a SHORT len ked je bearish. Blokuje obchody "
                "proti aktualnemu smeru trhu.",
    ),
    "showSR": dict(group="📏 Support/Resistance", title="Zobraz support/resistance",
        tooltip="Zapne/vypne kreslenie S/R ciar na grafe. Nema vplyv na obchodovanie z S/R urovni "
                "- to samostatne riadi 'Obchoduj z S/R urovni' v sekcii 🎯 Obchodovanie.",
    ),
    "srSwingLen": dict(group="📏 Support/Resistance", title="Swing lookback pre S/R (barov na kazdu stranu)",
        tooltip="Ako pri strukture - kolko barov na obe strany musi byt nizsie/vyssie aby sa bod "
                "pocital ako mozny support/resistance dotyk.",
    ),
    "srClusterPoints": dict(group="📏 Support/Resistance", title="Zhlukovanie urovni (body/points)", step=1.0,
        tooltip="Swingy vzdialene menej nez tolko cenovych bodov sa povazuju za dotyk tej istej "
                "urovne (nie ticky - rovnaka jednotka ako Min. velkost imbalance).",
    ),
    "srMinTouches": dict(group="📏 Support/Resistance", title="Min. pocet dotykov aby sa uroven zobrazila",
        tooltip="Kolko dotykov musi urovnen dosiahnut, aby sa vobec zobrazila ako S/R ciara na "
                "grafe - a zaroven (ak je zapnute obchodovanie z S/R) aby sa z nej presne pri "
                "tomto dotyku vytvorila obchodovatelna zona.",
    ),
    "srMaxLevels": dict(group="📏 Support/Resistance", title="Max pocet zobrazenych urovni",
        tooltip="Zobrazi sa najviac tolko urovni NAJBLIZSIE k aktualnej cene (nie podla poctu "
                "dotykov) - takze uz sa nemoze zobrazit uroven niekde daleko od ceny, kym blizsia "
                "zostane skryta.",
    ),
    "srLookbackDays": dict(group="📏 Support/Resistance", title="Zobrazuj urovne len za poslednych X dni",
        tooltip="Urovne (aj ich pocet dotykov) starsie nez tolko dni sa uplne zabudnu/vymazu - "
                "vhodne na skalpovanie, kde su relevantne len cerstve urovne, nie take spred "
                "tyzdnov.",
    ),
    "srZoneSaturationPct": dict(group="📏 Support/Resistance", title="Sýtosť farby zóny (%)", step=5.0,
        tooltip="Ako vyrazna/priesvitna je vyplnena farba tenkej S/R zony (aj GZ zluceneho zhluku) "
                "- vyssie cislo = sytejsia (menej priehladna), nizsie cislo = viac priesvitna. "
                "Netyka sa hrubky okraja zony (tu urcuje pocet dotykov, ako doteraz).",
    ),
    "showLiqSweep": dict(group="💧 Likvidita (Sweep)", title="Zobraz liquidity sweep (stop hunt)",
        tooltip="Zapne/vypne kreslenie liquidity sweep ('X') ciar a popiskov na grafe. Nema vplyv "
                "na obchodovanie zo sweepu - to samostatne riadi 'Obchoduj z likviditnych zon' v "
                "sekcii 🎯 Obchodovanie.",
    ),
    "liqSweepLen": dict(
        group="💧 Likvidita (Sweep)", title="Swing lookback pre likviditu (barov na kazdu stranu)",
        tooltip="Pocet barov na kazdu stranu, ktore musi swing high/low prekonat, aby bol "
                "povazovany za relevantny swing bod pre detekciu liquidity sweepu.",
    ),
    "liqSweepMinWick": dict(
        group="💧 Likvidita (Sweep)", title="Min. velkost prepichnutia (body/points)", step=0.5,
        tooltip="O kolko bodov minimalne musi cena prepichnut cez swing high/low, aby sa to "
                "zapocitalo ako pokus o sweep.",
    ),
    "liqSweepConfirmBars": dict(group="💧 Likvidita (Sweep)", title="Potvrdenie navratu do X barov",
        tooltip="Ak sa cena do tolkoto barov po prepichnuti zatvori spat pod/nad povodnu uroven, "
                "potvrdi sa to ako sweep. Ak nie, povazuje sa to skor za realny breakout (BOS), "
                "nie sweep.",
    ),
    "liqStrengthLen": dict(group="💧 Likvidita (Sweep)", title="Sila pivotu - okolie (barov)",
        tooltip="Zaznamenaju sa len naozaj SILNE/pivotne urovne - swing high/low musi byt "
                "najvyssi/najnizsi bod za poslednych tolko barov, inak sa ignoruje ako nevyznamny.",
    ),
    "showElliott": dict(group="🌊 Elliott Waves", title="Zobraz Elliott Waves (zapnut/vypnut)",
        tooltip="Hlavny vypinac celej Elliott Wave analyzy - ked je vypnuty, nekresli sa ziadne "
                "vlny, cislovanie ani projekcie. Elliott Waves sa v tejto strategii nepouzivaju na "
                "vstupy do obchodov, su len vizualna/analyticka pomocka.",
    ),
    "ewSwingLen": dict(group="🌊 Elliott Waves", title="Swing lookback pre zigzag (barov na kazdu stranu)",
        tooltip="Pocet barov na kazdu stranu pre zigzag swing detekciu, na ktorej je postavene "
                "cislovanie Elliott vln (0-1-2-3-4-5).",
    ),
    "ewMinWavePoints": dict(group="🌊 Elliott Waves", title="Min. velkost vlny (body/points)", step=1.0,
        tooltip="Filtruje nevyznamne mikro-kmity v zigzagu - vlna musi byt aspon takto velka.",
    ),
    "ewShowLabels": dict(group="🌊 Elliott Waves", title="Zobraz cislovanie vln (0-1-2-3-4-5)",
        tooltip="Zapne/vypne cislovanie vln (0,1,2,3,4,5) priamo na grafe pri kazdom zigzag bode.",
    ),
    "ewShowProjection": dict(group="🌊 Elliott Waves", title="Zobraz projekciu dalsej vlny (cielova zona)",
        tooltip="Zapne/vypne kreslenie cielovej zony pre dalsiu, este nedokoncenu vlnu - pocitanej "
                "kombinaciou 3 standardnych Fibonacci metod naraz.",
    ),
    "ewProjExtendBars": dict(group="🌊 Elliott Waves", title="O kolko barov dopredu kreslit projekcnu zonu",
        tooltip="O kolko barov dopredu (doprava od aktualneho baru) sa nakresli projekcna cielova "
                "zona dalsej vlny.",
    ),
    "ewLineColor": dict(group="🌊 Elliott Waves", title="Farba ciar a popisov vln", type="color",
        tooltip="Farba, ktorou sa kreslia vsetky ciary a popisky Elliott Wave analyzy.",
    ),
    "showImbalance": dict(group="🎨 Vizualizacia", title="Zobraz imbalance sviecky",
        tooltip="Zapne/vypne vykreslovanie farebneho boxu na sviecke, kde sa nasiel imbalance/gap "
                "(IMB entry model) alebo pin bar/engulfing pattern (Pin Bar/Engulfing entry "
                "model).",
    ),
    "showDashboard": dict(group="🎨 Vizualizacia", title="Zobraz dashboard panel",
        tooltip="Zapne/vypne cely dashboard panel (statistiky + volitelne tabulka obchodov) na "
                "grafe.",
    ),
    "dashPos": dict(group="🎨 Vizualizacia", title="Pozicia panelu",
        tooltip="V ktorom rohu grafu sa dashboard panel zobrazi.",
    ),
    "dashboardRows": dict(group="🎨 Vizualizacia", title="Pocet statistickych dlazdic (Obchody, Seria, ...)",
        tooltip="Kolko statistickych dlazdic (Obchody, Seria, Pozicia, Best win streak, Worst SL "
                "streak, Risk/obchod) sa v paneli zobrazi, v tomto poradi.",
    ),
    "showTradeLog": dict(group="🎨 Vizualizacia", title="Zobraz tabulku obchodov v paneli (Entry/SL/TP)",
        tooltip="Zapne/vypne tabulku poslednych obchodov (Entry/SL/TP/status) priamo v dashboard "
                "paneli, pod statistickymi dlazdicami.",
    ),
    "tradeLogRows": dict(group="🎨 Vizualizacia", title="Pocet riadkov v tabulke obchodov (max 20)",
        tooltip="Max. pocet riadkov (poslednych obchodov) zobrazenych v tabulke obchodov, ak je "
                "zapnuta vyssie.",
    ),
    "showDebugTable": dict(group="🎨 Vizualizacia", title="Zobraz pokročilý diagnostický panel",
        tooltip="Zapne/vypne dodatocnu diagnosticku tabulku s informaciami o orderoch cakajucich "
                "na vyplnenie - na ladenie/kontrolu vnutorneho stavu, nie na bezne pouzivanie.",
    ),
    "debugTableRows": dict(group="🎨 Vizualizacia", title="Počet riadkov v diagnostickom paneli",
        tooltip="Pocet riadkov zobrazenych v diagnostickom paneli, ak je zapnuty vyssie (vratane "
                "riadkov AKTUALNY/POSLEDNY obchod).",
    ),
    "debugPos": dict(group="🎨 Vizualizacia", title="Pozícia diagnostického panelu",
        tooltip="V ktorom rohu grafu sa diagnosticky panel zobrazi (nezavisle od pozicie "
                "dashboardu vyssie).",
    ),
    "imbLookback": dict(group="📦 SD Zony", title="Max barov dozadu pre IMB",
        tooltip="Kolko barov spatne (od aktualneho baru) sa hlada imbalance/gap pri IMB entry "
                "modeli (pri prvotnom aj opakovanom hladani gapu). Vyssia hodnota = najde aj "
                "starsie gapy, ale je narocnejsia na vypocet. Netyka sa Pin Bar/Engulfing modelu.",
    ),
    "imbMaxDistTicks": dict(group="📦 SD Zony", title="Max vzdialenost IMB od zony (ticky)",
        tooltip="Maximalna vzdialenost (v tickoch) medzi najdenym imbalance/gapom a hranicou zony, "
                "aby sa gap este povazoval za relevantny pre danu zonu (IMB entry model). Netyka "
                "sa Pin Bar/Engulfing modelu.",
    ),
    "minImbSizePoints": dict(group="📦 SD Zony", title="Min. velkost imbalance (body/points)", step=0.5,
        tooltip="Imbalance (medzera medzi sviecami) musi byt aspon takto velka (v cenovych bodoch, "
                "nie tickoch), inak sa neberie do uvahy - filtruje male, nevyznamne medzery.",
    ),
    "state1MaxBars": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="IMB model: Max. barov na výstup zo zóny",
        tooltip="IMB entry model: po najdeni gapu caka cena max tolkoto barov na to, aby sa pohla "
                "VON zo zony (potvrdenie odklonu) - inak sa zona zneplatni. Netyka sa Pin "
                "Bar/Engulfing modelu (ten prebehne cely v jednom bare).",
    ),
    "state2MaxBars": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="IMB model: Max. barov na potvrdenie",
        tooltip="IMB entry model: po vyjdeni ceny zo zony caka max tolkoto barov na potvrdenie "
                "zavretim za imbalance telom (viz 'Potvrdenie - ticky nad/pod IMB telom' nizsie) - "
                "inak sa zona zneplatni.",
    ),
    "state2ConfirmTicks": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="IMB model: Potvrdenie (ticky nad/pod IMB telom)",
        tooltip="IMB entry model: o kolko tickov musi close zavriet za telom najdeneho imbalance "
                "(nad nim pri LONG, pod nim pri SHORT), aby sa pohyb povazoval za potvrdeny a zona "
                "presla do fazy cakania na retest.",
    ),
    "state3MaxBars": dict(group="🔧 Pokročilé (časovanie vstupu, SL)", title="IMB model: Max. barov na retest",
        tooltip="IMB entry model: po potvrdeni caka cena max tolkoto barov na navrat/retest ku "
                "vstupnej cene (otvoreniu imbalance sviecky) - inak sa zona zneplatni. Nizka "
                "default hodnota (1) = ocakava retest prakticky hned na dalsom bare.",
    ),
    "state4MaxBars": dict(group="🔧 Pokročilé (časovanie vstupu, SL)", title="Rezerva (aktuálne nepoužívané)",
        tooltip="POZNAMKA: tento parameter momentalne nie je v kode nikde pouzity - vypocet SL/TP "
                "a umiestnenie orderu prebehne vzdy okamzite v tom istom bare, bez viacbaroveho "
                "cakania. Ponechane pre pripadne buduce pouzitie, teraz nema ziadny efekt na "
                "obchodovanie.",
    ),
    "state5MaxBars": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="Max. barov čakania na vyplnenie orderu",
        tooltip="Po umiestneni orderu caka strategia max tolkoto barov na jeho vyplnenie (fill) - "
                "ak sa nevyplni vcas, order sa zrusi a zona sa zneplatni. Plati pre vsetky tri "
                "entry modely (IMB/Pin Bar/Engulfing) rovnako.",
    ),
    "alertOnState2": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="Alert: cena opustila zónu (skorý signál)",
        tooltip="Posle alert ked cena exituje zo SD zony na strane imbalance (IMB model, skora "
                "faza procesu, este pred potvrdenim).",
    ),
    "alertOnState3": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="Alert: cena sa vrátila na vstupnú úroveň",
        tooltip="Posle alert ked sa cena vrati na otvorenie imbalance sviecky (IMB model, "
                "potvrdenie tesne pred umiestnenim orderu).",
    ),
    "alertOnState4": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="Alert: order umiestnený (E/SL/TP)",
        tooltip="Posle alert ked strategia umiestni order s cenami Entry/SL/TP",
    ),
    "rrRatio": dict(group="🎯 Obchodovanie", title="Risk:Reward pomer", step=0.5,
        tooltip="Pomer Take Profit ku Stop Lossu - TP vzdialenost = SL vzdialenost x tento pomer. "
                "Plati pre vsetky tri entry modely (IMB/Pin Bar/Engulfing) rovnako.",
    ),
    "slLookback": dict(
        group="🔧 Pokročilé (časovanie vstupu, SL)", title="SL: lookback barov od aktualnej sviecky",
        tooltip="IMB entry model: pocet barov spatne, v ktorych sa hlada najextremnejsi swing (low "
                "pre LONG, high pre SHORT) na umiestnenie Stop Lossu. Netyka sa Pin Bar/Engulfing "
                "modelu - tie pouzivaju vlastny wick patternu, nie tento lookback.",
    ),
    "slBufferTicks": dict(group="🔧 Pokročilé (časovanie vstupu, SL)", title="SL: buffer (ticky)",
        tooltip="Dodatocny odstup (v tickoch) Stop Lossu od swingu (IMB) alebo od opacneho wicku "
                "(Pin Bar/Engulfing) - male 'vankusik' proti presnemu dotyku urovne. Plati pre "
                "vsetky tri entry modely.",
    ),
    "maxLossDollar": dict(group="💰 Veľkosť pozície a riziko", title="Max strata ($, 0 = vypnute)", step=10.0,
        tooltip="Maximalna dolarova strata, ktoru ma order pri zasiahnuti SL sposobit - mnozstvo "
                "(qty) sa dopocitava automaticky podla vzdialenosti SL a hodnoty ticku nizsie. 0 = "
                "vypnute (vzdy sa pouzije qty=1).",
    ),
    "maxDailyWins": dict(group="💰 Veľkosť pozície a riziko", title="Max ziskovych tradov za den",
        tooltip="Ked pocet ZISKOVYCH obchodov v aktualnom dni dosiahne tuto hodnotu, dalsie nove "
                "ordery sa uz v ten den neposielaju - existujuce otvorene pozicie zostavaju bezat.",
    ),
    "tradeDirection": dict(group="🎯 Obchodovanie", title="Smer obchodov",
        tooltip="Ktorym smerom moze strategia obchodovat - Both=oba smery, Long only=len LONG "
                "(Demand zony), Short only=len SHORT (Supply zony).",
    ),
    "tickDollarValue": dict(
        group="💰 Veľkosť pozície a riziko", title="Hodnota jedneho ticku ($)", type="float", step=0.01,
        tooltip="Dolarova hodnota jedneho ticku pohybu pre 1 kontrakt/lot tohto instrumentu - "
                "pouziva sa na dopocet mnozstva (qty) z 'Max strata ($)' vyssie. Nastav podla "
                "specifikacie tvojho brokera/instrumentu.",
    ),
    "legacyPineSizing": dict(title="Pine sizing (1 kontrakt/BTC, ako TradingView)",
        tooltip="Doslovný Pine vzorec veľkosti pozície vrátane int() a max(1, …) — na BTC vždy 1 "
                "BTC bez ohľadu na maxLossDollar. Zapnúť len na porovnanie s TradingView. Vyžaduje "
                "tickDollarValue.",
    ),
    "atrLen": dict(title="ATR dĺžka pre jednotku „atr“",
        tooltip="Dĺžka ATR na grafovom TF, z ktorej sa prepočítavajú parametre zadané v jednotke "
                "atr. V Pine ATR nie je; slúži na prenos prahov medzi nástrojmi s inou cenovou "
                "škálou.",
    ),
    "minSlDistance": dict(title="Min. vzdialenosť SL od vstupu",
        tooltip="Obchod s tesnejším SL sa preskočí (SKIP: SL PRILIS TESNY). Poplatok je percento z "
                "nominálu, zisk rastie s R — tesné SL majú najhorší pomer edge k poplatku. 0 = "
                "vypnuté. Odporúčaná jednotka pct (0,20 % ceny), viď "
                "docs/merania/OPTIMALIZACIA_2026-09-05.md.",
    ),
    "leverage": dict(title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z risk-based "
                "sizingu, ktorá by sa inak na účet nezmestila (stake by sa orezal a riziko by bolo "
                "menšie než maxLossDollar).",
    ),
}
