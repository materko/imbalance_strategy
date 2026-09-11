"""Popisy parametrov Gap Fill pre formulár webapp.

Zdroj pravdy pre ľudské názvy a vysvetlenia. Rozsahy a defaulty sú v `config.py`
(`CONSTRAINTS` a defaulty dataclass), zoznamy hodnôt enumov sa dopĺňajú z `ENUM_FIELDS`.
"""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_SEANSA = "🕐 Seansa"
_MEDZERA = "📏 Medzera"
_VSTUP = "🚪 Vstup"
_CIEL = "🎯 Cieľ"
_STOP = "🛡️ Stop loss"
_RIADENIE = "⏱️ Riadenie pozície"
_RIZIKO = "💰 Riziko"
_VIZUAL = "🎨 Vizualizácia"
_PORT = "🧩 Rozšírenia portu"

#: Poradie skupín vo formulári.
GROUPS: tuple[str, ...] = (_SEANSA, _MEDZERA, _VSTUP, _CIEL, _STOP, _RIADENIE, _RIZIKO,
                           _VIZUAL, _PORT)

#: `pole configu -> {group, title, tooltip}`.
PARAMS: dict[str, dict[str, Any]] = {
    # ---- 🕐 Seansa -------------------------------------------------------- #
    "sessionTZ": dict(
        group=_SEANSA, title="Časové pásmo seansy",
        tooltip="V ktorom pásme sa počíta otvorenie. Medzera vzniká na otvorení burzy, "
                "takže pásmo musí sedieť na trh — indexy US na America/New_York.",
    ),
    "sessionStartH": dict(
        group=_SEANSA, title="Otvorenie seansy (H)",
        tooltip="Hodina otvorenia. Na tomto bare sa meria medzera. New York cash open je 9:30.",
    ),
    "sessionStartM": dict(group=_SEANSA, title="Otvorenie seansy (M)",
                          tooltip="Minúta otvorenia seansy."),
    "sessionEndH": dict(
        group=_SEANSA, title="Koniec seansy (H)",
        tooltip="Hodina, po ktorej sa už nevstupuje a zatvárajú sa pozície.",
    ),
    "sessionEndM": dict(group=_SEANSA, title="Koniec seansy (M)",
                        tooltip="Minúta konca seansy."),
    "weekdaysOnly": dict(group=_SEANSA, title="Obchoduj len Pondelok-Piatok",
                         tooltip="Vypne víkendové bary."),
    # ---- 📏 Medzera ------------------------------------------------------- #
    "minGapAtr": dict(
        group=_MEDZERA, title="Min. veľkosť medzery (ATR)", step=0.01,
        tooltip="Menšie medzery sa preskočia — nie je na nich čo zarobiť a spread ich zje. "
                "V ATR, aby prah platil na každom trhu.",
    ),
    "maxGapAtr": dict(
        group=_MEDZERA, title="Max. veľkosť medzery (ATR)", step=0.05,
        tooltip="Nad týmto sa medzera neobchoduje. Veľká medzera je správa, nie šum — "
                "vypĺňa sa zriedka a beží proti tebe ďaleko.",
    ),
    "requireInsideRange": dict(
        group=_MEDZERA, title="Len otvorenie vnútri včerajšieho rozsahu",
        tooltip="Ak dnešný open padol medzi včerajšie high a low, výplň je výrazne "
                "pravdepodobnejšia. Vypnutím vezmeš aj otvorenia mimo rozsahu.",
    ),
    "gapDirection": dict(
        group=_MEDZERA, title="Ktoré medzery obchodovať",
        tooltip="Gap up sa obchoduje na SHORT (späť dole k výplni), gap down na LONG. "
                "Na indexoch s rastovým biasom býva silnejší gap down.",
    ),
    # ---- 🚪 Vstup --------------------------------------------------------- #
    "entryMode": dict(
        group=_VSTUP, title="Typ vstupu",
        tooltip="open = hneď na prvom bare seansy (najviac obchodov, najviac falošných); "
                "confirm = až keď potvrdzovacia sviečka zavrie smerom k výplni (vyvážené); "
                "retest = po potvrdení sa čaká na návrat k otváracej cene (lepší RR, časť "
                "pohybov utečie).",
    ),
    "confirmMinutes": dict(
        group=_VSTUP, title="Potvrdenie: dĺžka sviečky (minúty)",
        tooltip="Koľko minút od otvorenia sa čaká na potvrdenie smeru. Prepočíta sa na bary "
                "podľa timeframu grafu.",
    ),
    "retestMaxBars": dict(
        group=_VSTUP, title="Retest: max barov na návrat",
        tooltip="Pri type vstupu retest: koľko barov po potvrdení sa čaká na návrat k otváracej "
                "cene. Potom sa setup zahadzuje.",
    ),
    "entryWindowMinutes": dict(
        group=_VSTUP, title="Vstup najneskôr do (minúty od otvorenia)",
        tooltip="Výplne sa dejú skoro — po tomto čase už šanca klesá. 0 = bez obmedzenia.",
    ),
    # ---- 🎯 Cieľ ---------------------------------------------------------- #
    "tpMode": dict(
        group=_CIEL, title="Výpočet cieľa",
        tooltip="gap = podiel medzery (100 % je celá výplň na včerajší close); "
                "rr = násobok vzdialenosti SL; atr = násobok ATR.",
    ),
    "targetPct": dict(
        group=_CIEL, title="Cieľ ako podiel medzery (%)",
        tooltip="100 % = úplná výplň. Nižšie číslo berie len časť medzery — viac ziskových "
                "obchodov, ale menších.",
    ),
    "rrRatio": dict(group=_CIEL, title="Risk:Reward pomer", step=0.1,
                    tooltip="Take profit = rrRatio × vzdialenosť SL."),
    "tpAtrMult": dict(group=_CIEL, title="TP vzdialenosť (násobok ATR)", step=0.1,
                      tooltip="Použije sa pri výpočte cieľa atr."),
    # ---- 🛡️ Stop loss ----------------------------------------------------- #
    "slMode": dict(
        group=_STOP, title="Umiestnenie SL",
        tooltip="atr = násobok ATR za vstup; gap_mult = násobok veľkosti medzery; "
                "open_bar = za extrém prvého baru seansy (najtesnejší).",
    ),
    "atrLen": dict(group=_STOP, title="ATR dĺžka",
                   tooltip="Dĺžka ATR (Wilder) pre všetky ATR jednotky."),
    "slAtrMult": dict(group=_STOP, title="SL vzdialenosť (násobok ATR)", step=0.1,
                      tooltip="Použije sa pri umiestnení SL nastavenom na atr."),
    "slGapMult": dict(group=_STOP, title="SL ako násobok medzery", step=0.1,
                      tooltip="Použije sa pri umiestnení SL nastavenom na gap_mult."),
    # ---- ⏱️ Riadenie pozície ---------------------------------------------- #
    "maxHoldMinutes": dict(
        group=_RIADENIE, title="Max. dĺžka obchodu (minúty)",
        tooltip="Keď sa medzera do tohto času nevyplní, obchod sa zatvára. 0 = bez limitu.",
    ),
    "closeAtSessionEnd": dict(group=_RIADENIE, title="Zatvor pozíciu na konci seansy",
                              tooltip="Intradenne: pozícia sa nedrží cez noc."),
    "enableTrailing": dict(group=_RIADENIE, title="Zapnúť trailing stop",
                           tooltip="Po dosiahnutí aktivačnej úrovne sa stop ťahá za cenou."),
    "trailActivationR": dict(group=_RIADENIE, title="Aktivácia trailingu (R-násobok)", step=0.1,
                             tooltip="Pri akom zisku v násobkoch rizika sa trailing zapne."),
    "trailOffsetR": dict(group=_RIADENIE, title="Trailing vzdialenosť (R-násobok)", step=0.1,
                         tooltip="Ako ďaleko za cenou sa stop ťahá, v násobkoch rizika."),
    # ---- 💰 Riziko -------------------------------------------------------- #
    "riskDollar": dict(group=_RIZIKO, title="Riziko na obchod ($)", step=10,
                       tooltip="Veľkosť pozície = riziko / vzdialenosť SL. 0 = 1 kontrakt."),
    # ---- 🎨 Vizualizácia -------------------------------------------------- #
    "showGap": dict(group=_VIZUAL, title="Kresliť medzeru",
                    tooltip="Zapne box medzery medzi včerajším close a dnešným open."),
    "showTarget": dict(group=_VIZUAL, title="Kresliť úroveň výplne",
                       tooltip="Zapne čiaru na včerajšom close, teda na cieli výplne."),
    # ---- 🧩 Rozšírenia portu ---------------------------------------------- #
    "tickDollarValue": dict(
        group=_PORT, title="Hodnota ticku ($)",
        tooltip="Koľko dolárov je pohyb o jeden tick na jeden kontrakt. CFD a futures "
                "nástroje to potrebujú na výpočet veľkosti pozície z rizika.",
    ),
    "legacyPineSizing": dict(
        group=_PORT, title="Pine sizing (1 kontrakt/BTC, ako TradingView)",
        tooltip="Doslovný Pine vzorec veľkosti pozície vrátane int() a max(1, …) — na BTC vždy "
                "1 BTC bez ohľadu na riziko. Zapnúť LEN na porovnanie s TradingView; pri qty < 1 "
                "sa limit rizika ticho neuplatní. Vyžaduje zadaný tickDollarValue.",
    ),
    "minSlDistance": dict(
        group=_PORT, title="Min. vzdialenosť SL od vstupu",
        tooltip="Obchod s tesnejším SL sa preskočí. Poplatok je percento z nominálu a zisk rastie "
                "s R, takže tesné stopy majú najhorší pomer edge k poplatku. 0 = vypnuté. "
                "Odporúčaná jednotka pct (napr. 0,20 % ceny).",
    ),
    "leverage": dict(
        group=_PORT, title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z "
                "risk-based sizingu, ktorá by sa inak na účet nezmestila.",
    ),
}
