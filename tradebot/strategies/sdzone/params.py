"""Popisy parametrov SD Zones pre formulár webapp."""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_DET = "🔍 Detekcia zóny"
_ZON = "📐 Zóna"
_VST = "🚪 Vstup"
_FIL = "🚦 Filtre"
_SL = "🛡️ Stop loss"
_TP = "🎯 Cieľ"
_RIA = "⏱️ Riadenie pozície"
_RIZ = "💰 Riziko"
_VIZ = "🎨 Vizualizácia"
_PORT = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_DET, _ZON, _VST, _FIL, _SL, _TP, _RIA, _RIZ, _VIZ, _PORT)

PARAMS: dict[str, dict[str, Any]] = {
    # ---- detekcia ----------------------------------------------------- #
    "baseMaxBars": dict(group=_DET, title="Báza: max. počet sviečok",
        tooltip="Z koľkých sviečok smie byť konsolidácia pred impulzom. Metodika hovorí o 2–4; "
                "dlhšia báza už nie je rozhodnutie trhu, ale bežné postávanie."),
    "baseMaxBodyPct": dict(group=_DET, title="Báza: max. podiel tela (%)",
        tooltip="Sviečka bázy smie mať telo najviac takúto časť svojho rozsahu. Malé telá = "
                "nerozhodnosť, presne to, čo má byť pred impulzom."),
    "baseMaxWidthAtr": dict(group=_DET, title="Báza: max. šírka (násobok ATR)",
        tooltip="Celý rozsah bázy musí byť užší než tento násobok ATR. Široká báza dá širokú "
                "zónu, tá zas ďaleký stop a zlý pomer rizika."),
    "impulseMinBodyAtr": dict(group=_DET, title="Impulz: min. telo (násobok ATR)",
        tooltip="Sviečka, ktorou cena zo zóny odchádza, musí mať aspoň takéto telo. Toto je "
                "hlavná páka na kvalitu zóny — slabý odchod znamená, že tam objednávky neboli."),
    "impulseMinBodyPct": dict(group=_DET, title="Impulz: min. podiel tela (%)",
        tooltip="Aká časť rozsahu impulznej sviečky musí byť telo. Odfiltruje sviečky s dlhými "
                "knôtmi, ktoré vyzerajú veľko, ale rozhodnutie v nich nie je."),
    "impulseMinMoveAtr": dict(group=_DET, title="Impulz: min. odchod od zóny (ATR)",
        tooltip="O koľko musí cena od zóny odísť, aby sa formácia počítala."),
    "impulseMaxBars": dict(group=_DET, title="Impulz: do koľkých barov",
        tooltip="Do koľkých barov od bázy musí cena ten odchod stihnúť."),
    # ---- zóna --------------------------------------------------------- #
    "zoneMode": dict(group=_ZON, title="Šírka zóny",
        tooltip="pfz = úzka zóna len z tiel bázy (Preferred Fresh Zone) — lepšia cena, ale cena "
                "ju častejšie minie; wfz = široká od knôtu po knôt (Wider Fresh Zone) — istejšie "
                "vyplnenie, horšia vstupná cena a ďalší stop."),
    "patterns": dict(group=_ZON, title="Ktoré formácie obchodovať",
        tooltip="all = všetky štyri; continuation = Rally-Base-Rally a Drop-Base-Drop (zóna "
                "v smere predošlého pohybu); reversal = Drop-Base-Rally a Rally-Base-Drop "
                "(zóna proti predošlému pohybu)."),
    "maxZoneAgeBars": dict(group=_ZON, title="Max. vek zóny (bary)",
        tooltip="Po koľkých baroch sa nedotknutá zóna zahodí. Stará zóna už nehovorí o dnešnom "
                "trhu."),
    "maxZones": dict(group=_ZON, title="Max. počet zón v pamäti",
        tooltip="Strop na počet sledovaných zón; najstaršie sa zahadzujú."),
    "requireFresh": dict(group=_ZON, title="Len čerstvé zóny (prvý dotyk)",
        tooltip="Zapnuté: obchoduje sa len prvý návrat do zóny. To je jadro metodiky — po prvom "
                "dotyku sa predpokladá, že objednávky sú vyplnené a zóna stratila význam."),
    # ---- vstup -------------------------------------------------------- #
    "tradeDirection": dict(group=_VST, title="Smer obchodov",
        tooltip="Both = obe strany; inak len longy alebo len shorty."),
    "entryMode": dict(group=_VST, title="Typ vstupu",
        tooltip="limit = limitka na okraji zóny (najlepšia cena, nemusí sa vyplniť); close = "
                "trhový vstup, keď sviečka zavrie vnútri zóny (istejšie, horšia cena); reject = "
                "čaká sa na sviečku, ktorá zónu odmietne a zavrie mimo nej (najprísnejšie)."),
    "entryDepthPct": dict(group=_VST, title="Hĺbka vstupu do zóny (%)",
        tooltip="0 % = limitka na bližšom okraji zóny, 100 % = na vzdialenejšom. Hlbšie = lepšia "
                "cena a tesnejší stop, ale menej vyplnených obchodov."),
    "maxTradesPerDay": dict(group=_VST, title="Max obchodov za deň",
        tooltip="Strop na počet vstupov za kalendárny deň."),
    # ---- filtre ------------------------------------------------------- #
    "weekdaysOnly": dict(group=_FIL, title="Obchoduj len Pondelok-Piatok",
        tooltip="Vypne víkendy — podstatné pre krypto."),
    "useTrendFilter": dict(group=_FIL, title="Filter trendu (kĺzavý priemer)",
        tooltip="Zapnuté: longy len nad priemerom, shorty pod ním. Metodika pracuje s kontextom "
                "vyššieho timeframu; toto je jeho najjednoduchšia náhrada."),
    "trendMaLen": dict(group=_FIL, title="Dĺžka priemeru pre filter trendu",
        tooltip="Počet barov kĺzavého priemeru, voči ktorému sa smer posudzuje."),
    "useTradeWindow": dict(group=_FIL, title="Obmedziť na obchodné okno",
        tooltip="Vypnuté: obchoduje sa kedykoľvek. Zapnuté: vstupy len v okne nižšie."),
    "tradeTZ": dict(group=_FIL, title="Časové pásmo okna",
        tooltip="Pásmo, v ktorom sú hodiny okna zadané."),
    "tradeStartH": dict(group=_FIL, title="Okno: začiatok (H)", tooltip="Hodina začiatku okna."),
    "tradeStartM": dict(group=_FIL, title="Okno: začiatok (M)", tooltip="Minúta začiatku okna."),
    "tradeEndH": dict(group=_FIL, title="Okno: koniec (H)", tooltip="Hodina konca okna."),
    "tradeEndM": dict(group=_FIL, title="Okno: koniec (M)", tooltip="Minúta konca okna."),
    # ---- stop loss ---------------------------------------------------- #
    "slMode": dict(group=_SL, title="Umiestnenie SL",
        tooltip="zone = za vzdialenejšiu hranu zóny plus buffer (tak to metodika robí); "
                "atr = pevný násobok ATR od vstupu."),
    "atrLen": dict(group=_SL, title="ATR dĺžka",
        tooltip="Počet barov pre ATR, z ktorého sa počítajú všetky prahy v jednotke atr."),
    "slBufferAtr": dict(group=_SL, title="Buffer za hranou zóny (ATR)",
        tooltip="Koľko sa pridá za hranu zóny, aby stop nezobral bežný šum."),
    "slAtrMult": dict(group=_SL, title="SL vzdialenosť (násobok ATR)",
        tooltip="Platí len pri umiestnení SL atr."),
    # ---- cieľ --------------------------------------------------------- #
    "tpMode": dict(group=_TP, title="Výpočet cieľa",
        tooltip="rr = násobok vzdialenosti SL; opposite = najbližšia opačná zóna (keď žiadna "
                "nie je, spadne na rr); atr = násobok ATR."),
    "rrRatio": dict(group=_TP, title="Risk:Reward pomer",
        tooltip="Metodika pracuje s 1:3 a viac — široký stop za zónou sa inak nezaplatí."),
    "tpAtrMult": dict(group=_TP, title="TP vzdialenosť (násobok ATR)", tooltip="Platí pri cieli atr."),
    # ---- riadenie ----------------------------------------------------- #
    "enableTrailing": dict(group=_RIA, title="Zapnúť trailing stop",
        tooltip="Po dosiahnutí aktivácie posúva SL za cenou."),
    "trailActivationR": dict(group=_RIA, title="Aktivácia trailingu (R-násobok)",
        tooltip="Pri akom zisku v násobkoch rizika sa trailing zapne."),
    "trailOffsetR": dict(group=_RIA, title="Trailing vzdialenosť (R-násobok)",
        tooltip="Ako ďaleko za cenou trailing SL ide."),
    "maxHoldBars": dict(group=_RIA, title="Max. dĺžka obchodu (bary)",
        tooltip="0 = vypnuté. Inak sa pozícia po toľkoto baroch zatvorí za trh."),
    "closeAtWindowEnd": dict(group=_RIA, title="Zatvor pozíciu na konci okna",
        tooltip="Platí len so zapnutým obchodným oknom."),
    # ---- riziko ------------------------------------------------------- #
    "riskDollar": dict(group=_RIZ, title="Riziko na obchod ($)",
        tooltip="Z neho a zo vzdialenosti SL sa počíta veľkosť pozície. 0 = 1 kus."),
    # ---- vizualizácia ------------------------------------------------- #
    "showZones": dict(group=_VIZ, title="Kresliť zóny", tooltip="Boxy supply a demand zón."),
    "showPatterns": dict(group=_VIZ, title="Kresliť štítky formácií",
        tooltip="Štítok RBR / DBD / DBR / RBD pri vzniku zóny."),
    # ---- rozšírenia portu --------------------------------------------- #
    "tickDollarValue": dict(group=_PORT, title="Hodnota ticku ($)",
        tooltip="CFD a futures ju potrebujú na risk-based sizing."),
    "legacyPineSizing": dict(group=_PORT, title="Pine sizing (1 kontrakt/BTC, ako TradingView)",
        tooltip="Doslovný Pine vzorec veľkosti pozície vrátane int() a max(1, …). Zapnúť LEN na "
                "porovnanie s TradingView; pri qty < 1 sa limit rizika ticho neuplatní."),
    "minSlDistance": dict(group=_PORT, title="Min. vzdialenosť SL od vstupu",
        tooltip="Obchod s tesnejším SL sa preskočí. 0 = vypnuté. Odporúčaná jednotka pct."),
    "leverage": dict(group=_PORT, title="Páka",
        tooltip="Páka vo Freqtrade futures. Nemení edge, len umožní otvoriť pozíciu z "
                "risk-based sizingu."),
}
