"""Popisy parametrov MTK ZONE pre formulár webapp. Rozsahy a defaulty sú v `config.py`.

Skupiny idú v poradí, v akom stratégia pracuje: odkiaľ sú zóny → pravidlá zón → volume profil → vstupné
modely → obchod → filtre → zobrazenie (rovnako ako Pine predloha).
"""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G1 = "1 · Zóny — odkiaľ sa berú"
_G2 = "2 · Zóny — pravidlá"
_G3 = "3 · Volume profil"
_G4 = "4 · Vstupné modely"
_G4A = "4a · IBS — nastavenie"
_G4B = "4b · Pin bar — nastavenie"
_G5 = "5 · Obchod"
_G6 = "6 · Filtre (proti prepadom)"
_G7 = "7 · Zobrazenie"
_G8 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filter trendu (spoločné obaly)"

GROUPS: tuple[str, ...] = (_G1, _G2, _G3, _G4, _G4A, _G4B, _G5, _G6, _G7, _G8, _GE)

_TF = "TF zón v minútach (≥ TF grafu). IBS, pin bar a limit idú z grafu (napr. 3m / 2m)."

PARAMS: dict[str, dict[str, Any]] = {
    "useZ1": dict(group=_G1, title="Zóny z TF 1", inline="z1", tooltip=_TF),
    "zoneTf1": dict(group=_G1, title="TF 1 (min)", inline="z1", tooltip=_TF),
    "useZ2": dict(group=_G1, title="Zóny z TF 2", inline="z2", tooltip=_TF),
    "zoneTf2": dict(group=_G1, title="TF 2 (min)", inline="z2", tooltip=_TF),
    "useClassic": dict(group=_G1, title="Klasické SD zóny (základňa + silný odchod)",
                       tooltip="Základňa 1–N malých sviečok a za ňou odchod s telom ≥ k × ATR."),
    "usePeak": dict(group=_G1, title="Vrchol volume profilu v zóne (POC / PEAK)",
                    tooltip="V zóne leží vrchol objemu profilu posledných N sviečok TF zón v čase vzniku."),
    "useVolSurge": dict(group=_G1, title="Zóny z klasického volume (nárast objemu po základni)",
                        tooltip="Sviečka s objemom ≥ k × priemer → späť na začiatok pohybu → tichá základňa pred ním."),
    "usePocZone": dict(group=_G1, title="Zóna priamo na POC a najväčšom PEAK",
                       tooltip="Bez SD vzoru, 1 potvrdenie (len pri Min. potvrdení = 1). POC sa posúva — veľa zón."),
    "pocEvery": dict(group=_G1, title="POC / PEAK zóna: prepočet každých (sviečky TF zón)"),
    "minConf": dict(group=_G2, title="Min. počet potvrdení zóny (1–3)",
                    tooltip="SD vzor, vrchol volume profilu v zóne, nárast klasického objemu. 2 = aspoň dve sa zhodnú."),
    "impMult": dict(group=_G2, title="Sila odchodu – klasická / profil (telo × ATR)", step=0.1),
    "volSpike": dict(group=_G2, title="Nárast objemu (× priemer objemu pred ním)", step=0.1),
    "impMultVol": dict(group=_G2, title="Sila odchodu pri náraste objemu (telo × ATR)", step=0.1),
    "baseMax": dict(group=_G2, title="Max. sviečok základne"),
    "baseBodyMax": dict(group=_G2, title="Max. telo sviečky základne (× ATR)", step=0.1),
    "minScore": dict(group=_G2, title="Min. kvalita zóny (0–100)",
                     tooltip="Sila odchodu 35 + objem odchodu 30 + najlepší zdroj 35."),
    "maxZones": dict(group=_G2, title="Max. aktívnych zón na stranu a TF",
                     tooltip="Pri plnom počte ustúpi zóna najďalej od ceny."),
    "atrLen": dict(group=_G2, title="ATR dĺžka", inline="atr"),
    "volLen": dict(group=_G2, title="Priemer objemu (sviečky)", inline="atr"),
    "lookback": dict(group=_G3, title="Počet sviečok profilu (TF zón)"),
    "rows": dict(group=_G3, title="Riadkov profilu"),
    "peakMin": dict(group=_G3, title="Min. % objemu pre PEAK", step=0.5),
    "useLimit": dict(group=_G4, title="Limit na zónu (bližšia hrana, SL za zónou)"),
    "useIBS": dict(group=_G4, title="IBS (gap → výstup zo zóny → potvrdenie → retest)"),
    "usePin": dict(group=_G4, title="Pin bar v zóne"),
    "modelBars": dict(group=_G4, title="Okno IBS / pin bar po dotyku zóny (sviečky)"),
    "imbLookback": dict(group=_G4A, title="Lookback gapu (sviečky)"),
    "minImbSize": dict(group=_G4A, title="Min. veľkosť gapu", inline="g"),
    "imbMaxDistTicks": dict(group=_G4A, title="Max. od zóny (ticky)", inline="g"),
    "st1Max": dict(group=_G4A, title="STATE1 výstup zo zóny (max sviečok)"),
    "st2Max": dict(group=_G4A, title="STATE2 potvrdenie (max sviečok)", inline="s2"),
    "st2ConfTicks": dict(group=_G4A, title="o ticky", inline="s2"),
    "st3Max": dict(group=_G4A, title="STATE3 retest (max sviečok)"),
    "st5Max": dict(group=_G4A, title="STATE5 platnosť limitu (sviečky)"),
    "ibsSlLookback": dict(group=_G4A, title="SL za swingom posledných (sviečky)"),
    "pbRatio": dict(group=_G4B, title="Knôt ≥ × telo", step=0.5),
    "pbBodyPos": dict(group=_G4B, title="Telo pri okraji (≤ % rozsahu)"),
    "pbMinRange": dict(group=_G4B, title="Min. rozsah sviečky"),
    "tradeDirection": dict(group=_G5, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "rrRatio": dict(group=_G5, title="RR (cieľ / riziko)", step=0.25, inline="rr"),
    "slBufTicks": dict(group=_G5, title="SL buffer (ticky)", inline="rr"),
    "fixedQty": dict(group=_G5, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G5, title="Kontraktov", inline="q"),
    "riskDollar": dict(group=_G5, title="Riziko $", inline="q"),
    "maxRiskTicks": dict(group=_G5, title="Max. riziko (ticky, 0 = bez limitu)"),
    "minGap": dict(group=_G5, title="Min. odstup medzi obchodmi (sviečky od výstupu)"),
    "maxDist": dict(group=_G5, title="Max. vzdialenosť vstupu od ceny (body, 0 = bez limitu)"),
    "vwapMode": dict(group=_G6, title="VWAP", options=["off", "with", "against"],
                     tooltip="with = long nad VWAP, short pod; against = long pod, short nad. Pri limite cena vstupu."),
    "vwapAnchor": dict(group=_G6, title="VWAP reset", options=["day", "ny", "week", "month"],
                       tooltip="day = obchodný deň CME (18:00 NY); ny = otvorenie New Yorku 9:30; week; month."),
    "useSess": dict(group=_G6, title="Len v seanse (čas New York)"),
    "sessStart": dict(group=_G6, title="Seansa od (HHMM)", inline="se"),
    "sessEnd": dict(group=_G6, title="do (HHMM)", inline="se"),
    "maxZoneAge": dict(group=_G6, title="Max. vek zóny pre limit (sviečky, 0 = bez)"),
    "minEntryScore": dict(group=_G6, title="Min. kvalita zóny pre vstup (0–100)"),
    "showZones": dict(group=_G7, title="Kresliť zóny"),
    "showIbsDraw": dict(group=_G7, title="Kresliť kroky IBS (iFVG, CB, retest)"),
    "leverage": dict(group=_G8, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
