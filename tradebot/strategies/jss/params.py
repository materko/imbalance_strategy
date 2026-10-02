"""Popisy parametrov JSS pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🧭 Štruktúra"
_G1 = "🟦 SD zóna"
_GF = "🔢 Fibonacci (noha BOS)"
_G2 = "🎯 Vstup"
_G3 = "🚦 Filtre a okno"
_G4 = "🛡️ Stop a ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"

GROUPS: tuple[str, ...] = (_G0, _G1, _GF, _G2, _G3, _G4, _G5, _G6, _G7)

PARAMS: dict[str, dict[str, Any]] = {
    "structTF": dict(group=_G0, title="TF struktury (min)",
                     tooltip="Na tomto TF sa hladaju swingy, BOS a zona. Musi byt nasobkom TF grafu; vstupne "
                             "modely bezia na grafe (nizsi TF)."),
    "refineTF": dict(group=_G0, title="TF upresnenia (min)",
                     tooltip="V zone TF struktury sa najde zona tohto nizsieho TF (napr. 4h -> 15m) a limitka ide "
                             "na nu. 0 = vypnute, obchoduje sa priamo zona TF struktury."),
    "swingLen": dict(group=_G0, title="Swing: barov z kazdej strany",
                     tooltip="Vrchol/dno je swing, ked je najvyssi/najnizsi aspon o tolkoto barov dolava aj doprava."),
    "triggerMode": dict(group=_G0, title="Spustac",
                        tooltip="bos = len prerazenie v smere trendu; choch = len zmena charakteru; both = oboje."),
    "atrLen": dict(group=_G0, title="ATR dlzka", tooltip="ATR na TF struktury (zona) aj na grafe (stop, imbalance)."),
    "zoneType": dict(group=_G1, title="Zona",
                     tooltip="ob = posledna opacna sviecka pred impulzom; base = baza pred impulzom (az N sviecok)."),
    "zoneEdge": dict(group=_G1, title="Hrana zony",
                     tooltip="wick = od knotu po knot; body = blizsia hrana na tele (vstup hlbsie)."),
    "impulseAtr": dict(group=_G1, title="Impulz: min. telo (ATR)",
                       tooltip="Prva sviecka v smere BOS s telom aspon tolko ATR je impulz; zona je pred nou."),
    "baseMaxBars": dict(group=_G1, title="Baza: max. sviecok", tooltip="Pri zone typu base."),
    "zoneMinAtr": dict(group=_G1, title="Zona: min. vyska (ATR)", tooltip="Uzsia zona sa neobchoduje. 0 = bez limitu."),
    "zoneMaxAtr": dict(group=_G1, title="Zona: max. vyska (ATR)", tooltip="Sirsia zona sa neobchoduje. 0 = bez limitu."),
    "zoneMaxAgeBars": dict(group=_G1, title="Platnost zony (bary struktury)",
                           tooltip="Po tolkych baroch struktury bez navratu zona zanikne. 0 = bez limitu."),
    "useFibo": dict(group=_GF, title="Filter Fibonacci",
                    tooltip="Fibo cez nohu, ktora BOS spravila (100 % = zaciatok, 0 % = extrem po BOS). Zona sa obchoduje, "
                            "len ked vstup lezi v zadanom pasme navratu."),
    "fibMinPct": dict(group=_GF, title="Navrat od (%)", inline="fib", step=0.1,
                      tooltip="Najmensi navrat nohy, pri ktorom sa este vstupuje. 50 = len v zlave, 61.8 = hlbsie."),
    "fibMaxPct": dict(group=_GF, title="do (%)", inline="fib", step=0.1,
                      tooltip="Najvacsi navrat. 100 = az po zaciatok nohy."),
    "entryModel": dict(group=_G2, title="Vstupny model",
                       tooltip="touch = limitka na hranu zony; imbalance / pinbar / any = po dotyku zony IBS "
                               "imbalance alebo pin bar na grafe, vstup na zavreti."),
    "entryDepthPct": dict(group=_G2, title="Limitka: hlbka v zone (%)",
                          tooltip="0 = na hrane zony, 50 = v strede. Plati aj pre dotyk pri imbalance / pin bar."),
    "confirmBars": dict(group=_G2, title="Po dotyku cakat barov",
                        tooltip="Kolko barov grafu po dotyku zony sa caka na imbalance / pin bar."),
    "imbMinSizeAtr": dict(group=_G2, title="Imbalance: min. medzera (ATR)", tooltip="ATR grafu."),
    "pbWickPct": dict(group=_G2, title="Pin bar: min. knot (% rozsahu)", tooltip="Knot proti smeru."),
    "pbBodyPct": dict(group=_G2, title="Pin bar: max. telo (% rozsahu)", tooltip="Telo sviecky."),
    "tradeDirection": dict(group=_G2, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G2, title="Max. obchodov za den", tooltip="Denny strop vstupov."),
    "cooldownBars": dict(group=_G2, title="Pauza po vstupe (bary)", tooltip="Kolko barov po vstupe sa nehlada dalsi."),
    "weekdaysOnly": dict(group=_G3, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G3, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G3, title="Casove pasmo okna", tooltip="Pasmo hodin okna a dna pre denny limit."),
    "tradeStartH": dict(group=_G3, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G3, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G3, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G3, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "slFrom": dict(group=_G4, title="Stop za zonu",
                   tooltip="refined = za upresnenu zonu nizsieho TF (tesnejsi stop); htf = za zonu TF struktury."),
    "slBufferAtr": dict(group=_G4, title="Stop za zonou (ATR)", tooltip="Rezerva stopu za protilahlou hranou zony v ATR."),
    "slBufferPoints": dict(group=_G4, title="Stop za zonou (body)",
                           tooltip="Rezerva stopu v bodoch ceny, keby cena vybrala likviditu za zonou. "
                                   "Pripocita sa k rezerve v ATR."),
    "tpMode": dict(group=_G4, title="Ciel",
                   tooltip="rr = nasobok stopu; structure = extrem nohy, ktora BOS spravila; extension = Fibonacciho extenzia nohy."),
    "rrRatio": dict(group=_G4, title="Risk:Reward", step=0.05, tooltip="TP = tento nasobok stopu."),
    "tpExtensionPct": dict(group=_G4, title="Extenzia (%)", step=0.1,
                           tooltip="Pri cieli extension: 27 = uroven -27 %, 61.8 = -61,8 %, 0 = koniec nohy."),
    "minRR": dict(group=_G4, title="Min. RR k cielu struktury", step=0.05,
                  tooltip="Pri cieli structure: blizsi ciel sa neobchoduje."),
    "maxHoldBars": dict(group=_G4, title="Casovy limit obchodu (bary)", tooltip="0 = bez limitu."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showStructure": dict(group=_G6, title="Kreslit BOS / CHoCH", tooltip="Prerazena uroven od swingu po prerazenie."),
    "showFibo": dict(group=_G6, title="Kreslit Fibonacci", tooltip="Urovne nohy BOS pri zapnutom filtri."),
    "showZones": dict(group=_G6, title="Kreslit zony", tooltip="SD zona od svojej sviecky po dotyk / koniec."),
    "tickDollarValue": dict(group=_G7, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G7, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G7, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G7, title="Paka", tooltip="Paka pre Freqtrade futures."),
}

# ---- typ vstupu market / limit (spoločný pre stratégie mimo IBS, `tradebot.core.entry_order`) ---- #
from tradebot.core.entry_order import entry_order_params  # noqa: E402

_GE = "🧾 Typ vstupu (market / limit)"
GROUPS = GROUPS + (_GE,)
PARAMS.update(entry_order_params(_GE))

# ---- filter trendu EMA (spoločný, `tradebot.core.entry_filter`) ---- #
from tradebot.core.entry_filter import entry_filter_params  # noqa: E402

PARAMS.update(entry_filter_params(_GE))
