"""Popisy parametrov Fibo pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📐 Noha (impulz)"
_G1 = "🔢 Urovne navratu"
_G2 = "🎯 Vstup"
_G3 = "🚦 Filtre a okno"
_G4 = "🛡️ Stop a ciel"
_G5 = "💰 Riziko"
_G6 = "🎨 Vizualizacia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "swingTF": dict(group=_G0, title="TF swingov (min)",
                    tooltip="Na tomto TF sa hladaju swingy a noha. Sklada sa z barov grafu, graf moze byt nizsi TF."),
    "swingLen": dict(group=_G0, title="Swing: barov z kazdej strany",
                     tooltip="Vrchol/dno je swing, ked je najvyssi/najnizsi aspon o tolkoto barov dolava aj doprava."),
    "legMinAtr": dict(group=_G0, title="Noha: min. dlzka (ATR)", tooltip="Kratsia noha nie je impulz. ATR na TF swingov."),
    "requireBreak": dict(group=_G0, title="Noha musi prekonat predosly swing",
                         tooltip="Rastuca noha konci nad predoslym swing vrcholom (klesajuca pod dnom) - jasny trend."),
    "legMaxBars": dict(group=_G0, title="Noha: max. barov", tooltip="Na TF swingov. 0 = bez limitu."),
    "atrLen": dict(group=_G0, title="ATR dlzka", tooltip="ATR na TF swingov aj na grafe."),
    "use382": dict(group=_G1, title="38,2 %", inline="fib", tooltip="Uroven navratu 38,2 %."),
    "use50": dict(group=_G1, title="50 %", inline="fib", tooltip="Uroven navratu 50 %."),
    "use618": dict(group=_G1, title="61,8 %", inline="fib", tooltip="Uroven navratu 61,8 %."),
    "use786": dict(group=_G1, title="78,6 %", inline="fib", tooltip="Uroven navratu 78,6 %."),
    "levelMode": dict(group=_G1, title="Kde obchodovat",
                      tooltip="zone = kdekolvek medzi najplytsou a najhlbsou zapnutou urovnou; levels = dno navratu "
                              "musi byt pri niektorej zapnutej urovni."),
    "levelTolAtr": dict(group=_G1, title="Tolerancia urovne (ATR)",
                        tooltip="Uroven je oblast: o kolko ATR grafu smie byt dno navratu od urovne."),
    "setupMaxBars": dict(group=_G1, title="Platnost setupu (bary TF swingov)",
                         tooltip="Kolko barov po potvrdeni nohy sa caka na navrat a vstup."),
    "entryModel": dict(group=_G2, title="Vstupny model",
                       tooltip="imbalance = IBS imbalance sviecka v smere nohy; pinbar = pin bar; any = jedno z nich."),
    "signalMaxBars": dict(group=_G2, title="Signal do (bary) po dne navratu",
                          tooltip="Vstupny signal najviac tolko barov grafu po sviecke s extremom navratu. 0 = bez limitu."),
    "imbMinSizeAtr": dict(group=_G2, title="Imbalance: min. medzera (ATR)", tooltip="ATR grafu."),
    "pbWickPct": dict(group=_G2, title="Pin bar: min. knot (% rozsahu)", tooltip="Knot proti smeru."),
    "pbBodyPct": dict(group=_G2, title="Pin bar: max. telo (% rozsahu)", tooltip="Telo sviecky."),
    "tradeDirection": dict(group=_G2, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G2, title="Max. obchodov za den", tooltip="Denny strop vstupov."),
    "weekdaysOnly": dict(group=_G3, title="Len pondelok-piatok", tooltip="Cez vikend sa neobchoduje."),
    "useTradeWindow": dict(group=_G3, title="Obchodne okno", tooltip="Vstupovat len v zadanych hodinach."),
    "tradeTZ": dict(group=_G3, title="Casove pasmo okna", tooltip="Pasmo hodin okna a dna pre denny limit."),
    "tradeStartH": dict(group=_G3, title="Okno od (H)", inline="tws", tooltip="Zaciatok okna - hodina."),
    "tradeStartM": dict(group=_G3, title="M", inline="tws", tooltip="Zaciatok okna - minuta."),
    "tradeEndH": dict(group=_G3, title="Okno do (H)", inline="twe", tooltip="Koniec okna - hodina."),
    "tradeEndM": dict(group=_G3, title="M", inline="twe", tooltip="Koniec okna - minuta."),
    "slMode": dict(group=_G4, title="Stop",
                   tooltip="leg = za zaciatok nohy (100 %); pullback = za extrem navratu."),
    "slBufferAtr": dict(group=_G4, title="Rezerva stopu (ATR)", tooltip="V ATR grafu."),
    "slBufferPoints": dict(group=_G4, title="Rezerva stopu (body)", tooltip="V bodoch ceny, pripocita sa."),
    "tpMode": dict(group=_G4, title="Ciel", tooltip="extension = extenzia nohy; rr = nasobok stopu."),
    "tpExtensionPct": dict(group=_G4, title="Extenzia (%)", step=0.1,
                           tooltip="27 = uroven -27 % (video), 61.8 = -61,8 %, 0 = koniec nohy."),
    "rrRatio": dict(group=_G4, title="Risk:Reward (pri rr)", step=0.05, tooltip="TP = tento nasobok stopu."),
    "minRR": dict(group=_G4, title="Min. RR k extenzii", step=0.05, tooltip="Blizsi ciel nez tolko R sa neobchoduje."),
    "maxHoldBars": dict(group=_G4, title="Casovy limit obchodu (bary)", tooltip="0 = bez limitu."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolaroch."),
    "showFibo": dict(group=_G6, title="Kreslit Fibonacci", tooltip="Noha a urovne pri obchodovanych setupoch."),
    "tickDollarValue": dict(group=_G7, title="Hodnota ticku ($)", type="float",
                            tooltip="Len pre Pine vzorec velkosti pozicie (legacyPineSizing)."),
    "legacyPineSizing": dict(group=_G7, title="Pine sizing", tooltip="Len na porovnanie s TradingView."),
    "minSlDistance": dict(group=_G7, title="Min. vzdialenost SL od vstupu",
                          tooltip="Obchod s tesnejsim stopom sa preskoci (% z ceny). 0 = vypnute."),
    "leverage": dict(group=_G7, title="Paka", tooltip="Paka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))

# ---- filter trendu EMA (spoločný, `tradebot.core.entry_filter`) ---- #
from tradebot.core.entry_filter import entry_filter_params  # noqa: E402

PARAMS.update(entry_filter_params(_GE))
