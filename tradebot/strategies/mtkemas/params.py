"""Popisy parametrov MTK EMAS pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_GM = "📈 Priemery a signál"
_GS = "🛡️ Stop a výstup"
_GR = "💰 Veľkosť"
_GX = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu, potvrdenie a filtre (filter trendu = EMA 200)"

GROUPS: tuple[str, ...] = (_GM, _GS, _GR, _GX, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "maType": dict(group=_GM, title="Typ priemeru",
                   tooltip="EMA, SMA, WMA, HMA, DEMA, TEMA, RMA, VWMA, KAMA — štúdia: rozhoduje menej než TF a dĺžka."),
    "signalMode": dict(group=_GM, title="Signál",
                       tooltip="price = zavretie prekríži priemer (slowLen); cross = rýchly priemer prekríži pomalý."),
    "fastLen": dict(group=_GM, title="Rýchly priemer (pri cross)", inline="len"),
    "slowLen": dict(group=_GM, title="Pomalý / jediný priemer", inline="len"),
    "tradeDirection": dict(group=_GM, title="Smer obchodov", tooltip="Štúdia: len longy (Long only)."),
    "atrLen": dict(group=_GS, title="ATR dĺžka", tooltip="ATR signálnej sviečky pre stop a trailing."),
    "slAtr": dict(group=_GS, title="Stop (× ATR)", step=0.25, tooltip="Počiatočný stop od vstupu."),
    "trailAtr": dict(group=_GS, title="Trailing (× ATR)", step=0.5, inline="tr",
                     tooltip="Stop ide za najlepšou cenou od vstupu o toľko ATR, späť nikdy. 0 = bez trailingu."),
    "trailFromR": dict(group=_GS, title="Trailing od (R)", step=0.5, inline="tr", tooltip="0 = hneď; 1 = až pri zisku 1 R."),
    "beAtR": dict(group=_GS, title="Zámok na vstup pri (R)", step=0.5,
                  tooltip="Pri zisku toľko R ide stop na cenu vstupu (break-even). 0 = vypnuté."),
    "rrTarget": dict(group=_GS, title="Cieľ (R)", step=0.5, tooltip="0 = bez pevného cieľa (trailing / opačné kríženie)."),
    "exitOnSignal": dict(group=_GS, title="Zavrieť pri opačnom krížení"),
    "fixedQty": dict(group=_GR, title="Pevný počet kontraktov", tooltip="Zapnuté = qty; vypnuté = veľkosť z rizika v $ k stopu."),
    "qty": dict(group=_GR, title="Počet kontraktov"),
    "riskDollar": dict(group=_GR, title="Riziko na obchod ($)"),
    "leverage": dict(group=_GX, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
