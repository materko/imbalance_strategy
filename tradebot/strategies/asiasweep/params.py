"""Popisy parametrov ASIA SWEEP 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🌏 Range Ázie (čas New York)"
_G1 = "🇬🇧 Sweep v Londýne"
_G2 = "🎯 Vstup"
_G3 = "📊 Volume profile — naked POC"
_G4 = "🛡️ Stop a cieľ"
_G5 = "💰 Veľkosť"
_G6 = "🎨 Vizualizácia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu a filtre"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "asiaStartH": dict(group=_G0, title="Ázia od (H)", inline="as", tooltip="Začiatok rangu Ázie. ICT: 20:00 New York."),
    "asiaStartM": dict(group=_G0, title="M", inline="as", tooltip="Minúta."),
    "asiaEndH": dict(group=_G0, title="do (H)", inline="ae", tooltip="Koniec rangu Ázie. ICT: 00:00 New York."),
    "asiaEndM": dict(group=_G0, title="M", inline="ae", tooltip="Minúta."),
    "rangeMinPct": dict(group=_G0, title="Min. veľkosť rangu (% z ceny)",
                        tooltip="Menší range sa neobchoduje. EURUSD: 0,1 % ≈ 11 pipov. 0 = vypnuté."),
    "rangeMaxPct": dict(group=_G0, title="Max. veľkosť rangu (% z ceny)",
                        tooltip="Väčší range sa neobchoduje (Ázia už vybehla). 0 = vypnuté."),
    "sweepStartH": dict(group=_G1, title="Sweep od (H)", inline="ss", tooltip="Londýnsky killzone 2:00 New York."),
    "sweepStartM": dict(group=_G1, title="M", inline="ss", tooltip="Minúta."),
    "sweepEndH": dict(group=_G1, title="do (H)", inline="se", tooltip="Londýnsky killzone do 5:00 New York."),
    "sweepEndM": dict(group=_G1, title="M", inline="se", tooltip="Minúta."),
    "sweepMin": dict(group=_G1, title="Min. prieraz za range (ATR)", tooltip="0 = stačí o tick."),
    "maxSweep": dict(group=_G1, title="Max. hĺbka sweepu (ATR)",
                     tooltip="Hlbší prieraz je už pokračovanie, nie vybratie likvidity — setup padá. 0 = vypnuté."),
    "requireReclaim": dict(group=_G1, title="Po prieraze zavretie späť v range",
                           tooltip="Vstup sa hľadá až keď sviečka zavrie späť v range Ázie."),
    "entryModel": dict(group=_G2, title="Vstupný model",
                       tooltip="imbalance = IBS (medzera medzi 1. a 3. sviečkou v smere); pinbar = dlhý knôt proti "
                               "smeru (aj samotná sviečka sweepu); any = jeden z nich; close = zavretie sviečky v smere."),
    "imbMinSize": dict(group=_G2, title="IBS: min. veľkosť medzery (ATR)", tooltip="Menšia medzera nie je imbalance."),
    "pbWickPct": dict(group=_G2, title="Pin bar: min. knôt (% rozsahu)", tooltip="Knôt proti smeru obchodu."),
    "pbBodyPct": dict(group=_G2, title="Pin bar: max. telo (% rozsahu)", tooltip="Telo pin baru."),
    "entryBars": dict(group=_G2, title="Vstup do N sviečok po sweepe", tooltip="Potom setup padá."),
    "entryEndH": dict(group=_G2, title="Vstup najneskôr do (H)", inline="ee", tooltip="Čas New York."),
    "entryEndM": dict(group=_G2, title="M", inline="ee", tooltip="Minúta."),
    "tradeDirection": dict(group=_G2, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "maxTradesPerDay": dict(group=_G2, title="Max. obchodov za deň", tooltip="1 = len prvý sweep dňa."),
    "weekdaysOnly": dict(group=_G2, title="Len pondelok–piatok", tooltip="Cez víkend sa nevstupuje."),
    "useNpoc": dict(group=_G3, title="Filter: v smere obchodu naked POC",
                    tooltip="Long len keď je nad cenou naked POC, short len keď je pod ňou (POC predošlého dňa, "
                            "ktorý cena ešte nedotkla) — trh tam má kam ísť."),
    "npocDays": dict(group=_G3, title="Naked POC z posledných N dní", tooltip="1 = len predošlý deň."),
    "vpStartH": dict(group=_G3, title="Deň profilu od (H)", inline="vs",
                     tooltip="Forex: 17:00 New York (koniec obchodného dňa). Začiatok = koniec → 24 h."),
    "vpStartM": dict(group=_G3, title="M", inline="vs", tooltip="Minúta."),
    "vpEndH": dict(group=_G3, title="do (H)", inline="ve", tooltip="Koniec dňa profilu."),
    "vpEndM": dict(group=_G3, title="M", inline="ve", tooltip="Minúta."),
    "vpRowTicks": dict(group=_G3, title="Riadok profilu (ticky)", tooltip="EURUSD: 10 tickov = 1 pip."),
    "slMode": dict(group=_G4, title="Stop",
                   tooltip="sweep = za extrém sweepu; signal = za signálnu sviečku (a dve pred ňou); atr = násobok ATR."),
    "slBuffer": dict(group=_G4, title="Rezerva za stop (ATR)", tooltip="Pri stope za sweep / signál."),
    "slAtr": dict(group=_G4, title="Stop (ATR)", tooltip="Pri slMode = atr."),
    "atrLen": dict(group=_G4, title="ATR dĺžka", tooltip="ATR grafu."),
    "tpMode": dict(group=_G4, title="Cieľ",
                   tooltip="rr = RR × stop; range = opačná strana rangu Ázie; mid = stred rangu; "
                           "npoc = najbližší naked POC v smere (bez neho RR)."),
    "rrRatio": dict(group=_G4, title="Risk:Reward", step=0.25, tooltip="Cieľ = RR × vzdialenosť stopu."),
    "useExitTime": dict(group=_G4, title="Zatvoriť v čase", inline="ex", tooltip="Otvorený obchod sa zavrie v tomto čase NY."),
    "exitH": dict(group=_G4, title="H", inline="ex", tooltip="Hodina (New York)."),
    "exitM": dict(group=_G4, title="M", inline="ex", tooltip="Minúta."),
    "fixedQty": dict(group=_G5, title="Pevná veľkosť", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G5, title="Veľkosť (loty / kontrakty)", tooltip="Pri pevnej veľkosti."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)", tooltip="Strata na stope v dolároch."),
    "showRange": dict(group=_G6, title="Kresliť range Ázie", tooltip="Box rangu."),
    "showSweeps": dict(group=_G6, title="Kresliť sweepy", tooltip="Značka prierazu maxima / minima."),
    "showNpoc": dict(group=_G6, title="Kresliť naked POC", tooltip="Čiara POC, kým ho cena nedotkne."),
    "leverage": dict(group=_G7, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_filter_params(_GE))
