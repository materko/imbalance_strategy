"""Popisy parametrov SWEEPING ENGULF 1.0 pre formulár webapp. Rozsahy a defaulty sú v `config.py`."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "🕯️ Signál"
_G1 = "🛡️ Stop a cieľ"
_G2 = "💰 Veľkosť"
_G3 = "🎨 Vizualizácia"
_G4 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu a filter trendu (EMA 200 z videa)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _G3, _G4, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "engulfMode": dict(group=_G0, title="Pohltenie", options=["range", "body"],
                       tooltip="range = zavretie za high (low) predošlej sviečky — pohltí ju celú (video); body = stačí za jej telo."),
    "prevCandle": dict(group=_G0, title="Predošlá sviečka", options=["opposite", "same", "any"],
                       tooltip="opposite = išla smerom manipulácie, proti obchodu (video „same direction“, lepšie výsledky); "
                               "same = v smere obchodu; any = hocijaká (video „mixed“)."),
    "tradeDirection": dict(group=_G0, title="Smer obchodov", tooltip="Both / Long only / Short only."),
    "slMethod": dict(group=_G1, title="Stop", options=["candle", "atr"],
                     tooltip="candle = za low / high signálnej sviečky (pôvodné video); atr = násobok ATR od vstupu."),
    "slBufferAtr": dict(group=_G1, title="Rezerva za sviečkou (ATR)", step=0.05, tooltip="Pri stope candle."),
    "atrLen": dict(group=_G1, title="ATR dĺžka", tooltip="Video: 14."),
    "atrMult": dict(group=_G1, title="Stop v ATR", step=0.5, tooltip="Pri stope atr; video skúšalo 1,5 až 5."),
    "rrRatio": dict(group=_G1, title="Cieľ (násobok stopu)", step=0.25, tooltip="Video: 1:2."),
    "fixedQty": dict(group=_G2, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G2, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_G2, title="Riziko na obchod ($)", tooltip="Pri veľkosti z rizika."),
    "showSignals": dict(group=_G3, title="Kresliť signály", tooltip="Štítok na signálnej sviečke."),
    "leverage": dict(group=_G4, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
