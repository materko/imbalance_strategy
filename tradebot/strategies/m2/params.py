"""Popisy parametrov M2 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = "📈 Trend (EMA zoradené)"
_G2 = "🎯 Vstup"
_G3 = "🛡️ Stop a cieľ"
_G4 = "💰 Veľkosť"
_G5 = "🎨 Vizualizácia"
_G6 = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G2, _G3, _G4, _G5, _G6, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    "useEmaTrend": dict(group=_G0, title="Len v smere zoradených EMA",
                        tooltip="Advanced: M2 len do trendu — long keď EMA 20 > 200 > 300 > 600 > 1200, short naopak."),
    "ema1": dict(group=_G0, title="EMA 1", inline="e1", tooltip="Najkratšia (podklad: 20)."),
    "ema2": dict(group=_G0, title="EMA 2", inline="e1", tooltip="Podklad: 200."),
    "ema3": dict(group=_G0, title="EMA 3", inline="e2", tooltip="Podklad: 300."),
    "ema4": dict(group=_G0, title="EMA 4", inline="e2", tooltip="Podklad: 600."),
    "ema5": dict(group=_G0, title="EMA 5", inline="e2", tooltip="Najdlhšia (podklad: 1200 na 1m)."),
    "emaNeedClose": dict(group=_G0, title="… a zavretie za najkratšou EMA", tooltip="Long len pri zavretí nad EMA 1."),
    "allowLong": dict(group=_G2, title="Longy", tooltip="M2 = posledná negatívna sviečka (zavretie pod 50 % rozsahu) pred pohybom hore."),
    "allowShort": dict(group=_G2, title="Shorty", tooltip="M2 = posledná pozitívna sviečka (zavretie nad 50 %) pred pohybom dole."),
    "limitMaxBars": dict(group=_G2, title="Limitka čaká najviac (sviečok, 0 = do zániku)",
                         tooltip="Bez limitu čaká, kým sviečka nezavrie za stopom alebo ju nenahradí novšia potvrdená M2."),
    "useWindow": dict(group=_G2, title="Len v okne (New York)", tooltip="Podklad okno neuvádza — predvolene celý deň."),
    "entryStartH": dict(group=_G2, title="Od (H)", inline="es", tooltip="Hodina New York."),
    "entryStartM": dict(group=_G2, title="M", inline="es", tooltip="Minúta."),
    "entryEndH": dict(group=_G2, title="Do (H)", inline="ee", tooltip="Hodina New York."),
    "entryEndM": dict(group=_G2, title="M", inline="ee", tooltip="Minúta."),
    "maxTradesPerDay": dict(group=_G2, title="Max obchodov za deň (0 = bez)", tooltip="Deň New York."),
    "slTicks": dict(group=_G3, title="Stop za M2 (tickov)", tooltip="Podklad: stop pod low M2 (long) / nad high M2 (short)."),
    "rrRatio": dict(group=_G3, title="RRR (cieľ = RR × riziko)", step=0.1, tooltip="Podklad: 3 : 1 do trendu, advanced skalp 2 : 1."),
    "riskDollar": dict(group=_G4, title="Riziko na obchod ($)", tooltip="Pri vypnutom pevnom počte."),
    "showZones": dict(group=_G5, title="Kresliť M2", tooltip="Box M2 od sviečky po potvrdenie."),
    "leverage": dict(group=_G6, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
