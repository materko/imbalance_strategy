"""Popisy parametrov NY VA BREAKOUT pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📊 Fixed range (čas New York)"
_G1 = "🎯 Vstup"
_G2 = "🛡️ Stop a cieľ"
_G6 = "🧭 Filtre (VWAP, šírka VA)"
_G3 = "💰 Veľkosť"
_G4 = "🎨 Vizualizácia"
_G5 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G6, _G2, _G3, _G4, _G5, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "rangeStartH": dict(group=_G0, title="Range od (H)", inline="rs", tooltip="Začiatok profilu, čas New York (9:30 = 15:30 SK)."),
    "rangeStartM": dict(group=_G0, title="M", inline="rs", tooltip="Minúta."),
    "rangeEndH": dict(group=_G0, title="Range do (H)", inline="re",
                      tooltip="Koniec profilu (10:30 NY = 16:30 SK). Bar, ktorý sa v tomto čase otvára, už do profilu nepatrí."),
    "rangeEndM": dict(group=_G0, title="M", inline="re", tooltip="Minúta."),
    "profileRows": dict(group=_G0, title="Počet riadkov profilu", tooltip="Cenové riadky medzi low a high rangeu."),
    "valueAreaPct": dict(group=_G0, title="Value area (%)", step=1,
                         tooltip="Podiel objemu okolo POC; od POC sa pridáva vždy objemnejší susedný riadok."),
    "allowLong": dict(group=_G1, title="Long nad VAH", tooltip="Zavretie sviečky nad VAH → long."),
    "allowShort": dict(group=_G1, title="Short pod VAL", tooltip="Zavretie sviečky pod VAL → short."),
    "entryEndH": dict(group=_G1, title="Vstupy do (H)", inline="en", tooltip="Posledný čas vstupu, New York."),
    "entryEndM": dict(group=_G1, title="M", inline="en", tooltip="Minúta."),
    "maxTradesPerDay": dict(group=_G1, title="Max obchodov za deň",
                            tooltip="Ďalší vstup len po skončení predošlého a po novom prieraze úrovne."),
    "confirmCloses": dict(group=_G1, title="Zavretí za úrovňou (potvrdenie)",
                          tooltip="Koľko zavretí po sebe nad VAH / pod VAL je prieraz. 2 = menej falošných prierazov."),
    "entryMode": dict(group=_G1, title="Vstup", tooltip="close = market po prieraze; retest = limitka na VAH / VAL po prieraze (bližší stop, lepšie RR)."),
    "retestBars": dict(group=_G1, title="Retest platí (barov)", tooltip="Nevyplnená limitka sa po toľkých baroch zruší."),
    "useVwap": dict(group=_G6, title="Len v smere VWAP", tooltip="Long len nad VWAP, short len pod. VWAP obchodného dňa od 18:00 NY."),
    "vaMinPoints": dict(group=_G6, title="Šírka VA min (body, 0 = bez)", inline="va", tooltip="Pod touto šírkou sa v ten deň neobchoduje."),
    "vaMaxPoints": dict(group=_G6, title="max", inline="va", tooltip="Nad touto šírkou sa v ten deň neobchoduje (trh už vybehol)."),
    "maxSlPoints": dict(group=_G2, title="Max stop (body, 0 = bez)", inline="ms", tooltip="POC môže byť ďaleko — obmedzí veľkosť stopu."),
    "maxSlAtr": dict(group=_G2, title="Max stop (× ATR, 0 = bez)", inline="ms", step=0.1, tooltip="ATR 14 grafu; platí menšia z oboch hraníc."),
    "slCapMode": dict(group=_G2, title="Stop nad limit", tooltip="skip = obchod vynechať, cap = skrátiť stop na limit."),
    "rrRatio": dict(group=_G2, title="RRR (cieľ = RR × riziko)", step=0.1, tooltip="Riziko = vzdialenosť vstupu od stopu za POC."),
    "slBufferTicks": dict(group=_G2, title="Rezerva SL za POC (ticky)", tooltip="Long: stop pod POC, short: nad POC."),
    "useCloseTime": dict(group=_G2, title="Zavrieť pozíciu v čase", tooltip="Inak sa pozícia drží do stopu alebo cieľa."),
    "closeH": dict(group=_G2, title="Zavrieť o (H)", inline="cl", tooltip="Čas New York."),
    "closeM": dict(group=_G2, title="M", inline="cl", tooltip="Minúta."),
    "fixedQty": dict(group=_G3, title="Pevný počet kontraktov", tooltip="Vypnuté = veľkosť z rizika v $."),
    "qty": dict(group=_G3, title="Počet kontraktov", tooltip="Pri pevnom počte."),
    "riskDollar": dict(group=_G3, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte."),
    "showLevels": dict(group=_G4, title="Kresliť range, POC, VAH, VAL", tooltip="Box rangeu a úrovne až do konca vstupov."),
    "leverage": dict(group=_G5, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
