"""Popisy parametrov CRT + TBS pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕯️ Range (CRT)"
_G1 = "🐢 Vyber (turtle soup)"
_G2 = "🎯 Vstup"
_G3 = "🚦 Filtre a okno"
_G4 = "🛡️ Stop a ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "rangeTF": dict(group=_G0, title="TF rangu (min)",
                    tooltip="Sviecka tohto vyssieho TF je range (CRH = high, CRL = low). 240 = 4h. Sklada sa z barov grafu."),
    "rangeMinAtr": dict(group=_G0, title="Range: min. vyska (ATR)", tooltip="V ATR vyssieho TF. 0 = bez limitu."),
    "rangeMaxAtr": dict(group=_G0, title="Range: max. vyska (ATR)", tooltip="V ATR vyssieho TF. 0 = bez limitu."),
    "sweepWithinBars": dict(group=_G0, title="Vyber do (sviecky vyssieho TF)",
                            tooltip="V kolkych sviecach vyssieho TF po range sviecke musi prist vyber. Klasika: 1."),
    "validBars": dict(group=_G0, title="Platnost setupu (sviecky vyssieho TF)",
                      tooltip="Kolko sviecok vyssieho TF po range sviecke sa caka na vstup. 2 = manipulacia + distribucia."),
    "requireHtfClose": dict(group=_G0, title="Cakat na zavretie manipulacnej sviecky",
                            tooltip="Vstup az po tom, co sviecka vyssieho TF s vyberom zavrie spat v rangu."),
    "requireOldHL": dict(group=_G0, title="Len stary vrchol / dno",
                         tooltip="Vyberana hranica musi byt aj najvyssim / najnizsim bodom za N sviecok vyssieho TF."),
    "keyLookback": dict(group=_G0, title="Stary vrchol / dno: sviecok dozadu", tooltip="Pri zapnutom filtri."),
    "atrLen": dict(group=_G0, title="ATR dlzka", tooltip="ATR vyssieho TF (range) aj grafu (stop)."),
    "sweepKind": dict(group=_G1, title="Druh vyberu",
                      tooltip="body = TBS, sviecka grafu zavrie za hranicou; wick = staci knot; any = oboje."),
    "sweepMaxAtr": dict(group=_G1, title="Max. vybeh za hranicu (ATR)",
                        tooltip="Hlbsi vybeh uz nie je vyber, ale prerazenie. 0 = bez limitu."),
    "entryModel": dict(group=_G2, title="Vstupny model",
                       tooltip="model1 = sviecka zavrie spat v rangu a za predoslou sviecou; cisd = zavretie za otvorenim "
                               "posledneho tahu k extremu; mss_fvg = prerazenie swingu s medzerou, limitka do medzery."),
    "swingLen": dict(group=_G2, title="Swing grafu: barov z kazdej strany", tooltip="Pre MSS."),
    "fvgValidBars": dict(group=_G2, title="Limitka do medzery plati (bary)", tooltip="Pri mss_fvg."),
    "tradeDirection": dict(group=_G2, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G2, title="Max. obchodov za den", tooltip="Denny strop vstupov."),
    "weekdaysOnly": dict(group=_G3, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G3, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G3, title="Casove pasmo okna", tooltip="Pasmo hodin okna a dna pre denny limit."),
    "tradeStartH": dict(group=_G3, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G3, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G3, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G3, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "slBufferAtr": dict(group=_G4, title="Stop za extrem vyberu (ATR)", tooltip="Rezerva v ATR grafu."),
    "slBufferPoints": dict(group=_G4, title="Stop za extrem vyberu (body)", tooltip="Rezerva v bodoch ceny, pripocita sa."),
    "tpMode": dict(group=_G4, title="Ciel",
                   tooltip="mid = stred rangu (50 %); opposite = opacny koniec rangu; rr = nasobok stopu."),
    "rrRatio": dict(group=_G4, title="Risk:Reward (pri rr)", step=0.05, tooltip="TP = tento nasobok stopu."),
    "minRR": dict(group=_G4, title="Min. RR k cielu v rangu", step=0.05,
                  tooltip="Pri mid / opposite: blizsi ciel nez tolko R sa neobchoduje."),
    "maxHoldBars": dict(group=_G4, title="Casovy limit obchodu (bary)", tooltip="0 = bez limitu."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showRanges": dict(group=_G6, title="Kreslit range", tooltip="Range (CRH-CRL) a jeho stred pri setupoch s vyberom."),
    "showSweeps": dict(group=_G6, title="Kreslit vybery", tooltip="Stitok TS na sviecke, ktora hranicu prekrocila."),
    "tickDollarValue": dict(group=_G7, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G7, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G7, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G7, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
