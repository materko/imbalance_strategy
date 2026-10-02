"""Popisy parametrov Scalping 3MA + RSI + fraktál pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📈 Trend (tri SMMA)"
_G1 = "📊 RSI"
_G2 = "🔺 Fraktal a vstup"
_G3 = "🚦 Filtre a okno"
_G4 = "🛡️ Stop a ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "ma1Len": dict(group=_G0, title="SMMA rychly", inline="ma", tooltip="Video: 20."),
    "ma2Len": dict(group=_G0, title="stredny", inline="ma", tooltip="Video: 60."),
    "ma3Len": dict(group=_G0, title="pomaly", inline="ma", tooltip="Video: 200."),
    "requireMaOrder": dict(group=_G0, title="Priemery zoradene",
                           tooltip="Short len ked 20 < 60 < 200 (long naopak). Video to nevyzaduje."),
    "rsiLen": dict(group=_G1, title="RSI dlzka", tooltip="Predvolene 14."),
    "rsiLevel": dict(group=_G1, title="RSI uroven", tooltip="Pod nou short, nad nou long. Video: 50."),
    "rsiExit": dict(group=_G1, title="Zavriet pri RSI cez uroven",
                    tooltip="Obchod sa zavrie, ked RSI prejde cez uroven proti nemu (video)."),
    "fractalLen": dict(group=_G2, title="Fraktal: barov z kazdej strany", tooltip="Williams fraktal = 2."),
    "fractalSide": dict(group=_G2, title="Ktory fraktal",
                        tooltip="pullback = short po fraktale hore, long po fraktale dole (sipka indikatora v smere obchodu); "
                                "trend = naopak; any = ktorykolvek."),
    "tradeDirection": dict(group=_G2, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G2, title="Max. obchodov za den", tooltip="Video odporuca 1."),
    "cooldownBars": dict(group=_G2, title="Pauza po vstupe (bary)", tooltip="Kolko barov po vstupe sa nehlada dalsi."),
    "weekdaysOnly": dict(group=_G3, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G3, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G3, title="Casove pasmo okna", tooltip="Pasmo hodin okna a dna pre denny limit."),
    "tradeStartH": dict(group=_G3, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G3, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G3, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G3, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "slMode": dict(group=_G4, title="Stop",
                   tooltip="points = pevne body ceny (video: 5 pipov); atr = nasobok ATR; fractal = za extrem fraktalu."),
    "slPoints": dict(group=_G4, title="Stop (body ceny)", tooltip="EURUSD: 5 pipov = 0,0005."),
    "slAtr": dict(group=_G4, title="Stop (ATR)", tooltip="Pri slMode = atr."),
    "slBufferAtr": dict(group=_G4, title="Rezerva za fraktal (ATR)", tooltip="Pri slMode = fractal."),
    "atrLen": dict(group=_G4, title="ATR dlzka", tooltip="Predvolene 14."),
    "rrRatio": dict(group=_G4, title="Risk:Reward", step=0.05, tooltip="Video: 1 : 2 (5 pipov na 10)."),
    "beAtR": dict(group=_G4, title="Stop na vstup po zisku (R)", step=0.25,
                  tooltip="Po zisku tolkych R sa stop posunie na cenu vstupu. 0 = vypnute."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showMa": dict(group=_G6, title="Kreslit priemery", tooltip="Tri SMMA ako lomene ciary."),
    "showFractals": dict(group=_G6, title="Kreslit fraktaly signalov", tooltip="Fraktal, ktory splnil podmienky."),
    "tickDollarValue": dict(group=_G7, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G7, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G7, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G7, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
