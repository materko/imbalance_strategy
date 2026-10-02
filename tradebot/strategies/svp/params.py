"""Popisy parametrov Volume Profile POC pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📊 Volume profile (seansa)"
_G1 = "🎯 Vstup"
_G2 = "🚦 Okno obchodovania"
_G3 = "🛡️ Stop a ciel"
_G4 = "💰 Riziko"
_G5 = "🎨 Vizualizacia"
_G6 = "🧩 Rozšírenia portu"
_GF = "🔢 Fibonacci (konfluencia s POC)"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GF, _G2, _G3, _G4, _G5, _G6, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "sessionStartH": dict(group=_G0, title="Seansa od (H)", inline="ss", tooltip="Zaciatok seansy profilu, New York. 9:30 = cash seansa."),
    "sessionStartM": dict(group=_G0, title="M", inline="ss", tooltip="Minuta."),
    "sessionEndH": dict(group=_G0, title="Seansa do (H)", inline="se", tooltip="Koniec seansy profilu, New York."),
    "sessionEndM": dict(group=_G0, title="M", inline="se", tooltip="Minuta."),
    "rowTicks": dict(group=_G0, title="Vyska riadku (ticky)", tooltip="Cenovy riadok profilu. MNQ: 4 ticky = 1 bod."),
    "valueAreaPct": dict(group=_G0, title="Value area (%)", tooltip="Podiel objemu okolo POC. Klasika 70."),
    "pocSource": dict(group=_G0, title="Ktory POC",
                      tooltip="previous = POC predoslej seansy (pevna uroven cely den); developing = vyvijajuci sa POC dnesnej seansy."),
    "tradeMode": dict(group=_G1, title="Co obchodovat",
                      tooltip="rejection = cena pod POC: short na dotyk, nad POC: long; retest = len po prerazeni POC zavretim, "
                              "vstup pri navrate k nemu; both = oboje."),
    "entryModel": dict(group=_G1, title="Vstupny model",
                       tooltip="touch = limitka na POC; imbalance / pinbar / any = po dotyku IBS imbalance alebo pin bar, vstup na zavreti."),
    "awayAtr": dict(group=_G1, title="Odchod od POC (ATR)",
                    tooltip="Cena musi najprv zavriet aspon tolko ATR od POC - az potom je navrat k nemu dotyk."),
    "touchTolAtr": dict(group=_G1, title="Tolerancia dotyku (ATR)", tooltip="Pre vstupne modely; limitka je presne na POC."),
    "breakBufferAtr": dict(group=_G1, title="Prerazenie: buffer (ATR)", tooltip="Zavretie za POC aspon o tolko ATR."),
    "retestMaxBars": dict(group=_G1, title="Retest do (bary)", tooltip="Kolko barov po prerazeni sa navrat pocita ako retest."),
    "confirmBars": dict(group=_G1, title="Po dotyku cakat barov", tooltip="Na vstupny model."),
    "imbMinSizeAtr": dict(group=_G1, title="Imbalance: min. medzera (ATR)", tooltip="ATR grafu."),
    "pbWickPct": dict(group=_G1, title="Pin bar: min. knot (% rozsahu)", tooltip="Knot proti smeru."),
    "pbBodyPct": dict(group=_G1, title="Pin bar: max. telo (% rozsahu)", tooltip="Telo sviecky."),
    "tradeDirection": dict(group=_G1, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G1, title="Max. obchodov za den", tooltip="Denny strop vstupov."),
    "useFibo": dict(group=_GF, title="Filter Fibonacci",
                    tooltip="POC sa obchoduje, len ked lezi v pasme navratu poslednej nohy v smere obchodu "
                            "(long: rastuca noha, short: klesajuca). 100 % = zaciatok nohy, 0 % = jej koniec."),
    "fibMinPct": dict(group=_GF, title="Navrat od (%)", inline="fib", step=0.1, tooltip="Plytsia hranica pasma. Klasika 38,2."),
    "fibMaxPct": dict(group=_GF, title="do (%)", inline="fib", step=0.1, tooltip="Hlbsia hranica pasma. Klasika 78,6."),
    "fibSwingTF": dict(group=_GF, title="TF swingov (min)", tooltip="Na akom TF sa hladaju swingy nohy. Sklada sa z grafu."),
    "fibSwingLen": dict(group=_GF, title="Swing: barov z kazdej strany", tooltip="Pivot potvrdeny tolkymi barmi vlavo aj vpravo."),
    "fibLegMinAtr": dict(group=_GF, title="Min. dlzka nohy (ATR)", tooltip="ATR na TF swingov. Kratsia noha sa nepouzije."),
    "weekdaysOnly": dict(group=_G2, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G2, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach (New York)."),
    "tradeStartH": dict(group=_G2, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G2, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G2, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G2, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "closeAtWindowEnd": dict(group=_G2, title="Zavriet na konci okna", tooltip="Otvorena pozicia sa zavrie, ked okno skonci."),
    "slMode": dict(group=_G3, title="Stop",
                   tooltip="atr = nasobok ATR od vstupu; points = pevne body ceny; leg = za zaciatok Fibonacciho nohy (len s filtrom Fibonacci)."),
    "slBufferAtr": dict(group=_G3, title="Rezerva za nohu (ATR)", tooltip="Pri slMode = leg."),
    "slAtr": dict(group=_G3, title="Stop (ATR)", tooltip="Pri slMode = atr."),
    "slPoints": dict(group=_G3, title="Stop (body)", tooltip="Pri slMode = points."),
    "atrLen": dict(group=_G3, title="ATR dlzka", tooltip="Predvolene 14."),
    "tpMode": dict(group=_G3, title="Ciel",
                   tooltip="rr = nasobok stopu; va_edge = hrana value area (long VAH, short VAL); "
                           "extension = Fibonacciho extenzia nohy (len s filtrom Fibonacci)."),
    "tpExtensionPct": dict(group=_G3, title="Extenzia (%)", step=0.1, tooltip="Ciel za koncom nohy. Klasika 27 alebo 61,8."),
    "rrRatio": dict(group=_G3, title="Risk:Reward (pri rr)", step=0.05, tooltip="TP = tento nasobok stopu."),
    "minRR": dict(group=_G3, title="Min. RR k cielu (hrana VA / extenzia)", step=0.05, tooltip="Blizsi ciel sa neobchoduje."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showPoc": dict(group=_G5, title="Kreslit POC", tooltip="POC predoslej seansy cez nasledujuci den."),
    "showValueArea": dict(group=_G5, title="Kreslit value area", tooltip="VAH a VAL predoslej seansy."),
    "showFibo": dict(group=_G5, title="Kreslit Fibonacci", tooltip="Noha a urovne pri obchode s filtrom Fibonacci."),
    "tickDollarValue": dict(group=_G6, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G6, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G6, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G6, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
