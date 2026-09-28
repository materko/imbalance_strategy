"""Popisy parametrov Drift VWAP pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`
(`CONSTRAINTS` a defaulty dataclass), zoznamy hodnôt enumov sa dopĺňajú z `ENUM_FIELDS`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕐 Seansa"
_G1 = "📈 VWAP a drift"
_G2 = "🚀 Vstup (pullback)"
_G2b = "💥 Prerazenie VWAP"
_G3 = "🛡️ Stop loss"
_G4 = "🎯 Ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G2b, _G3, _G4, _G5, _G6, _G7)

PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🕐 Seansa ---------------------------------------------------- #
    "sessionStartH": dict(
        group=_G0, title="Otvorenie seansy (H)",
        tooltip="Hodina otvorenia New York cash seansy v pasme America/New_York (standardne 9:30 NY). "
                "Od nej sa obchoduje a pri kotve 'ny_open' sa od nej pocita aj VWAP.",
    ),
    "sessionStartM": dict(group=_G0, title="Otvorenie seansy (M)", tooltip="Minuta otvorenia seansy."),
    "sessionEndH": dict(
        group=_G0, title="Koniec seansy (H)",
        tooltip="Hodina, po ktorej sa uz nevstupuje a otvorena pozicia sa zatvara (ak je zapnute "
                "zatvaranie na konci seansy). Standardne 15:55 NY.",
    ),
    "sessionEndM": dict(group=_G0, title="Koniec seansy (M)", tooltip="Minuta konca seansy."),
    "weekdaysOnly": dict(
        group=_G0, title="Len pracovne dni",
        tooltip="Vypne sobotu a nedelu. Na futures bez ucinku, na krypte odfiltruje vikendy.",
    ),
    # ---- 📈 VWAP a drift ------------------------------------------------ #
    "vwapAnchor": dict(
        group=_G1, title="Kotva VWAP",
        tooltip="Odkial sa VWAP pocita. 'ny_open' = od 9:30 New York, len cash seansa (ako vo videu). "
                "'session' = klasicky seansovy VWAP CME futures od 18:00 NY (Globex) - tak ho ukazuje "
                "TradingView s kotvou Session na NQ/MNQ. 'utc_day' = den od 00:00 UTC, klasika na krypte. "
                "Obchodne okno sa kotvou nemeni.",
    ),
    "vwapPeriod": dict(
        group=_G1, title="VWAP zo sviečok",
        tooltip="'15' = VWAP z 15-minutovych sviecok zlozenych z grafu (ako vo videu: VWAP z 15m grafu "
                "zobrazeny na 5m); meni sa pri zatvoreni 15m sviecky a drift sa meria v 15m sviečkach. "
                "'chart' = priamo z barov grafu, meni sa na kazdom bare.",
    ),
    "driftBars": dict(
        group=_G1, title="Drift za periód",
        tooltip="Drift = o kolko sa VWAP zmenil za tolkoto posledných period VWAP (15m sviecok, resp. "
                "barov grafu). Pri 15m a 2 je to posledna pol hodina.",
    ),
    "driftMinAtr": dict(
        group=_G1, title="Min. drift (ATR)",
        tooltip="Kolko sa VWAP musi za 'Drift za period' pohnut, aby to bol jasny smer dna - v nasobkoch "
                "ATR grafu. Pod prahom je den bez smeru a neobchoduje sa.",
    ),
    # ---- 🚀 Vstup ------------------------------------------------------ #
    "tradeDirection": dict(
        group=_G2, title="Smer obchodov",
        tooltip="Both = long pri stupajucom VWAP aj short pri klesajucom. Long only / Short only obmedzi "
                "na jeden smer.",
    ),
    "awayAtr": dict(
        group=_G2, title="Odchod od VWAP (ATR)",
        tooltip="Kolko musi cena zavriet nad VWAP (long) alebo pod nim (short), aby sa navrat k nemu "
                "pocital ako pullback. To je 'jasny ustaleny pohyb' z videa; 0 = staci byt na spravnej strane.",
    ),
    "touchTolAtr": dict(
        group=_G2, title="Tolerancia dotyku (ATR)",
        tooltip="Pullback = low baru (short: high) pride k VWAP blizsie nez tato tolerancia. Vstupuje sa "
                "market na zavreti toho baru, ak zavrie spat na strane driftu; ak zavrie za VWAP, "
                "pullback prerazil a obchod nie je.",
    ),
    "entryMode": dict(
        group=_G2, title="Druh vstupu",
        tooltip="close = market na zavreti sviecky, ktora sa dotkla VWAP a zavrela spat na strane driftu. "
                "limit = limitka priamo na VWAP (+/- tolerancia) lezi, kym cena nepride. "
                "stop = po dotyku stop order nad high (short: pod low) pullbackovej sviecky. "
                "reaction = cena sa dotkne VWAP a vstupuje sa na close prvej reakcnej sviecky do protipohybu "
                "(long prva byčia). pinbar = prvy pin bar po dotyku. engulfing = prva pohlcujuca sviecka. "
                "Potvrdenie sa caka najviac 'Potvrdenie do (barov)'; ked cena zavrie za VWAP, pullback prerazil.",
    ),
    "stopValidBars": dict(
        group=_G2, title="Stop order plati (barov)",
        tooltip="Pri vstupe 'stop': kolko barov lezi stop order za pullbackovou svieckou, kym sa zrusi.",
    ),
    "confirmBars": dict(
        group=_G2, title="Potvrdenie do (barov)",
        tooltip="V kolkych baroch od dotyku VWAP (vratane neho) musi prist vstupna sviecka - pri close, "
                "stop, reaction, pinbar aj engulfing. Pri limit sa nepouziva.",
    ),
    "pbWickPct": dict(
        group=_G2, title="Pin bar: knot min. %",
        tooltip="Knot smerom k VWAP (long spodny) musi byt aspon tolkoto percent rozpatia sviecky.",
    ),
    "pbBodyPct": dict(
        group=_G2, title="Pin bar: telo max. %",
        tooltip="Telo pin baru smie byt najviac tolkoto percent rozpatia sviecky.",
    ),
    "failCloseAtr": dict(
        group=_G2, title="Prerazenie VWAP (ATR)",
        tooltip="Pullback je prerazeny (a caka sa uz len na dalsi den / dalsi odchod), az ked sviecka zavrie "
                "za VWAP o viac nez tolkoto ATR. Zavretie kusok pod VWAP (long) je stale pullback a reakcna "
                "sviecka po nom sa obchoduje.",
    ),
    "firstPullbackOnly": dict(
        group=_G2, title="Len prvy pullback",
        tooltip="Obchoduje sa len prvy pullback dna v danom smere (ako vo videu) - aj ked prerazil a obchod "
                "nevznikol. Vypnute = po novom odchode od VWAP sa pocita dalsi pullback.",
    ),
    "everyBounce": dict(
        group=_G2, title="Kazdy odraz od VWAP",
        tooltip="Zapnute = obchoduje sa kazdy odraz od VWAP v smere dna, nie len prvy pullback. Dalsi odraz "
                "chce, aby cena po predoslom dotyku znova odisla od VWAP aspon o 'Odchod pred dalsim odrazom'. "
                "Strop je 'Max odrazov za den'; 'Len prvy pullback' a 'Max obchodov za den' sa vtedy nepouzivaju.",
    ),
    "bounceAwayAtr": dict(
        group=_G2, title="Odchod pred dalsim odrazom (ATR)",
        tooltip="Pri 'Kazdy odraz': o kolko ATR musi cena po dotyku znova zavriet od VWAP, aby dalsi dotyk bol "
                "novy odraz. Prvy odchod dna je stale 'Odchod od VWAP'. 0 = staci zavriet na spravnej strane.",
    ),
    "maxBouncesPerDay": dict(
        group=_G2, title="Max odrazov za den",
        tooltip="Pri 'Kazdy odraz': kolko odrazov sa za den najviac obchoduje.",
    ),
    "tradeBreakout": dict(
        group=_G2b, title="Obchodovat prerazenie VWAP",
        tooltip="Zapnute = obchoduje sa aj prerazenie VWAP: cena zavrela na jednej strane VWAP a dalsia sviecka "
                "zavrie na druhej aspon o 'Prerazenie o (ATR)'. Vstup market na zavreti v smere prerazenia, "
                "stop podla 'Druh stopu' (pullback = za extrem prerazovacej sviecky). Nezavisle od odrazov.",
    ),
    "breakoutAtr": dict(
        group=_G2b, title="Prerazenie o (ATR)",
        tooltip="Kolko ATR za VWAP musi prerazovacia sviecka zavriet. Strana VWAP sa meni len zavretim mimo "
                "tolerancie dotyku, takze sviecky motajuce sa na VWAP prerazenie nevyrobia.",
    ),
    "breakoutWithBias": dict(
        group=_G2b, title="Prerazenie len v smere dna",
        tooltip="Zapnute = len prerazenie v smere driftu (long pri stupajucom VWAP). Vypnute = oba smery, aj "
                "prerazenie proti driftu (zlyhany pullback ako otocka).",
    ),
    "maxBreakoutsPerDay": dict(
        group=_G2b, title="Max prerazeni za den",
        tooltip="Kolko prerazeni sa za den najviac obchoduje (nezavisle od odrazov).",
    ),
    "entryDelayMinutes": dict(
        group=_G2, title="Vstup najskor po (min)",
        tooltip="Kolko minut po otvoreni sa este nevstupuje. Pri VWAP z 15m je prva hodnota az o 9:45 "
                "a drift za 2 periody o 10:15, takze skor aj tak nic nevznikne.",
    ),
    "entryWindowMinutes": dict(
        group=_G2, title="Okno na vstup (min)",
        tooltip="Dokedy po otvoreni sa este vstupuje. 0 = az do konca seansy.",
    ),
    "maxTradesPerDay": dict(
        group=_G2, title="Max obchodov za den",
        tooltip="Strop na pocet vstupov za den (oba smery spolu).",
    ),
    # ---- 🛡️ Stop loss ---------------------------------------------------- #
    "atrLen": dict(
        group=_G3, title="Dlzka ATR",
        tooltip="ATR na baroch grafu; v jeho nasobkoch su vsetky prahy strategie.",
    ),
    "slMode": dict(
        group=_G3, title="Druh stopu",
        tooltip="pullback = za extrem pullbacku (od dotyku po vstup), nikdy nie blizsie nez VWAP; pri limitke "
                "extrem este nie je, ide za VWAP. candle = pod low (short: nad high) vstupnej sviecky - pri "
                "reaction / pinbar / engulfing je to reakcna (potvrdzovacia) sviecka. vwap = za VWAP. atr = 'Stop ATR' x ATR od vstupu. "
                "swing = za najnizsi low (short: najvyssi high) poslednych 'Swing barov'. Okrem atr sa pridava "
                "rezerva stopu.",
    ),
    "slBufferAtr": dict(
        group=_G3, title="Rezerva stopu (ATR)",
        tooltip="Kolko ATR za uroven stopu (pullback, VWAP, swing) sa stop posunie.",
    ),
    "slAtr": dict(
        group=_G3, title="Stop ATR (druh atr)",
        tooltip="Pri druhu stopu 'atr': vzdialenost stopu od vstupu v nasobkoch ATR.",
    ),
    "slSwingBars": dict(
        group=_G3, title="Swing barov (druh swing)",
        tooltip="Pri druhu stopu 'swing': z kolkych poslednych barov (vratane vstupneho) sa berie extrem.",
    ),
    "minSlDistance": dict(
        group=_G3, title="Min. vzdialenost SL",
        tooltip="Obchod s tesnejsim stopom sa preskoci (poplatok je percento z nominalu, tesne stopy maju "
                "najhorsi pomer edge k poplatku). 0 = vypnute.",
    ),
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    "rrRatio": dict(
        group=_G4, title="Pomer RR", step=0.25,
        tooltip="Ciel = tolkoto nasobkov vzdialenosti stopu. Video ciel neuvadza; 2 je vychodisko na test.",
    ),
    "closeAtSessionEnd": dict(
        group=_G4, title="Zatvorit na konci seansy",
        tooltip="Otvorena pozicia sa zatvori na konci seansy - strategia je intradenna.",
    ),
    # ---- 💰 Riziko -------------------------------------------------------- #
    "riskDollar": dict(
        group=_G5, title="Riziko na obchod ($)",
        tooltip="Kolko dolarov stoji jeden stop; velkost pozicie sa dopocita zo vzdialenosti stopu.",
    ),
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    "showVwap": dict(
        group=_G6, title="Kreslit VWAP",
        tooltip="Ciara VWAP v grafe behu, farbena driftom: zelena = VWAP stupa, cervena = klesa, "
                "siva = bez jasneho smeru.",
    ),
    # ---- 🧩 Rozšírenia portu ---------------------------------------------- #
    "tickDollarValue": dict(
        group=_G7, title="Hodnota ticku ($)",
        tooltip="Kolko dolarov je jeden tick (MNQ 0,25 bodu = 0,50 $). Potrebne na velkost pozicie z rizika "
                "pri futures a CFD.",
    ),
    "legacyPineSizing": dict(
        group=_G7, title="Pine vzorec velkosti",
        tooltip="Doslovny Pine vzorec velkosti pozicie (int + max 1). Len na porovnanie s TradingView.",
    ),
    "leverage": dict(
        group=_G7, title="Paka (Freqtrade)",
        tooltip="Paka vo Freqtrade futures. Na MultiCharts bez ucinku.",
    ),
}
