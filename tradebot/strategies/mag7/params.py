"""Popisy parametrov Mag7 + SPX sila pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params
from tradebot.core.types import INSTRUMENTS

__all__ = ["GROUPS", "PARAMS"]

_G0 = "⏱️ Vstup"
_G1 = "✅ Potvrdenie na Nasdaqu (symbol grafu)"
_G2 = "🚪 Výstup"
_G3 = "💪 Sila pohybu"
_G4 = "📊 Symboly"
_G5 = "💰 Veľkosť"
_G6 = "🎨 Vizualizácia"
_G7 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _G5, _G6, _G7, _GE)

#: Ponuka symbolov sily: akcie z IBKR a indexy z Dukascopy.
_SYMBOLS = sorted(k for k, i in INSTRUMENTS.items()
                  if (i.source or i.venue) == "ibkr" or k in ("us500_dukascopy", "nas100_dukascopy", "dj30_dukascopy"))
_VWAP_DATA = ["mnq_databento", "nas100_dukascopy", "us500_dukascopy"]

PARAMS: dict[str, dict[str, Any]] = {
    "thr": dict(group=_G0, title="Prah sily (long ≥ +prah, short ≤ −prah)", step=0.5,
                tooltip="Sila je od −10 do +10. Pine default 5."),
    "waitMin": dict(group=_G0, title="Meranie sily od (minút po otvorení NY)",
                    tooltip="Prvých N minút sa sila len počíta; bežný pohyb sa meria v tej istej minúte."),
    "entryEnd": dict(group=_G0, title="Podmienky sa musia splniť do (minút po otvorení NY)",
                     tooltip="Okno vstupu od waitMin do entryEnd (zavretie sviečky grafu); jeden obchod za deň."),
    "openH": dict(group=_G0, title="Otvorenie NY: hodina", inline="op", tooltip="Čas New York."),
    "openM": dict(group=_G0, title="minúta", inline="op", tooltip="Čas New York."),
    "allowL": dict(group=_G0, title="Long", inline="dir", tooltip="Povoliť longy."),
    "allowS": dict(group=_G0, title="Short", inline="dir", tooltip="Povoliť shorty."),
    "useVwap": dict(group=_G1, title="Long len nad VWAP, short len pod VWAP (VWAP od 9:30 NY)",
                    tooltip="Zavretie sviečky grafu voči VWAP od otvorenia NY."),
    "useEma": dict(group=_G1, title="Long len nad EMA, short len pod EMA", tooltip="EMA na TF grafu."),
    "emaLen": dict(group=_G1, title="EMA dĺžka", tooltip="Pine default 100; v TradingView používané 50."),
    "useMag": dict(group=_G1, title="Long len nad čiarou MAG7, short len pod",
                   tooltip="Čiara MAG7 = kde by Nasdaq bol, keby sa od 9:30 pohol ako vážený priemer Mag7 + SPX."),
    "magLen": dict(group=_G1, title="Čiara MAG7: dĺžka EMA (sviečky grafu)", tooltip="Vyhladenie čiary MAG7."),
    "useOpen": dict(group=_G1, title="Navyše: long len nad open NY, short len pod",
                    tooltip="Cena musí byť od open NY aspoň o min. pohyb."),
    "minMove": dict(group=_G1, title="Min. pohyb od open NY (body)", tooltip="Pri zapnutom filtri open NY."),
    "vwapData": dict(group=_G1, title="VWAP z 1m dát nástroja", options=_VWAP_DATA,
                     tooltip="Pine počíta VWAP z 1m. Keď graf nie je tento nástroj, VWAP sa skladá zo sviečok grafu."),
    "slMode": dict(group=_G2, title="Druh stopu",
                   tooltip="points = stop v bodoch od vstupu; open = za open NY + rezerva "
                           "(keď je open na zlej strane vstupu, použijú sa body)."),
    "slPts": dict(group=_G2, title="Stop v bodoch od vstupu", tooltip="Pine default 20."),
    "slOpenBuf": dict(group=_G2, title="Rezerva za open NY (body)", tooltip="Pine default 2."),
    "rr": dict(group=_G2, title="RRR (cieľ = násobok stopu)", step=0.25, tooltip="Cieľ zo skutočného stopu."),
    "useEod": dict(group=_G2, title="Zatvoriť v čase (NY)", inline="eod",
                   tooltip="Otvorený obchod sa zavrie na zavretí sviečky v tomto čase."),
    "eodH": dict(group=_G2, title="H", inline="eod", tooltip="Hodina (New York)."),
    "eodM": dict(group=_G2, title="M", inline="eod", tooltip="Minúta."),
    "sessEndH": dict(group=_G3, title="Koniec NY seansy (H)", inline="se",
                     tooltip="Pine 0930-1600; sila a VWAP sa počítajú len v seanse."),
    "sessEndM": dict(group=_G3, title="M", inline="se", tooltip="Minúta konca seansy."),
    "typDays": dict(group=_G3, title="Bežný pohyb: priemer z posledných dní",
                    tooltip="Priemer |pohybu po waitMin minútach| z toľkých predošlých dní (aspoň 3)."),
    "zFull": dict(group=_G3, title="Plný bod pri pohybe = × bežný pohyb", step=0.1,
                  tooltip="Pohyb symbolu v násobkoch bežného pohybu; plná veľkosť pri tomto násobku."),
    "wMag": dict(group=_G3, title="Váha: veľkosť pohybu", step=0.5, tooltip="Váha veľkosti pohybu v sile."),
    "wBreadth": dict(group=_G3, title="Váha: zhoda symbolov", step=0.5, tooltip="Váha zhody smeru symbolov."),
    "spxW": dict(group=_G3, title="Váha SPX", step=0.5, tooltip="Váha indexu (symbol 8)."),
    "stockW": dict(group=_G3, title="Váha akcií Mag7", step=0.5,
                   tooltip="Váha symbolov 1–7. 1 = verzia 1.0 (sila zo všetkých 8 symbolov); 0 = sila len zo SPX — "
                           "tak to počíta TradingView, keď mu akcie vrátia prázdnu hodnotu."),
    **{f"s{k}": dict(group=_G4, title=f"Symbol {k}", options=_SYMBOLS,
                     tooltip="Kľúč nástroja, z ktorého 1m dát sa počíta pohyb od otvorenia.")
       for k in range(1, 8)},
    "s8": dict(group=_G4, title="Index (S&P 500)", options=_SYMBOLS,
               tooltip="Dukascopy US500 = CFD na S&P 500 (pohyb ako SP:SPX)."),
    "fixedQty": dict(group=_G5, title="Pevný počet kontraktov",
                     tooltip="Ako Pine (počet kontraktov). Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G5, title="Počet kontraktov", tooltip="Pine default 1."),
    "riskDollar": dict(group=_G5, title="Riziko na obchod ($)",
                       tooltip="Pri vypnutom pevnom počte: strata na stope v dolároch."),
    "showLines": dict(group=_G6, title="Kresliť VWAP, MAG7, EMA a open NY", tooltip="Čiary počas NY seansy."),
    "leverage": dict(group=_G7, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
