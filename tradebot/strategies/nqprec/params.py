"""Popisy parametrov NQ PRECISION 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '🕘 Range a spúšť (New York, HHMM)'
_G1 = '📏 Filtre'
_G2 = '🛡️ Stop, cieľ a čas'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _G2, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'rangeStart': dict(group=_G0, title='Začiatok OR', inline='r', tooltip=''),
    'rangeEnd': dict(group=_G0, title='Koniec OR', inline='r', tooltip=''),
    'useTriggerTime': dict(group=_G0, title='Snímka v čase', tooltip='Predloha: 9:59:55 ET.'),
    'triggerTime': dict(group=_G0, title='Čas snímky (zavretie baru)', tooltip='9:59:55 → zavretie 1m baru 9:59 = 10:00.'),
    'tradeUntil': dict(group=_G0, title='Prieraz do (bez snímky)', tooltip=''),
    'useFilters': dict(group=_G1, title='Filtre RVOL a ATR', tooltip=''),
    'rvolLen': dict(group=_G1, title='RVOL z barov', tooltip='Okno sa každý deň vynuluje (predloha).'),
    'rvolMin': dict(group=_G1, title='RVOL od', inline='rv', tooltip=''),
    'rvolMax': dict(group=_G1, title='do', inline='rv', tooltip=''),
    'atrRegimeLen': dict(group=_G1, title='Dlhé ATR', tooltip=''),
    'regimeMin': dict(group=_G1, title='ATR / dlhé ATR od', inline='rg', tooltip=''),
    'regimeMax': dict(group=_G1, title='do', inline='rg', tooltip=''),
    'atrPeriod': dict(group=_G2, title='ATR', tooltip=''),
    'atrSlMult': dict(group=_G2, title='Stop (× ATR)', inline='sl', tooltip=''),
    'atrTpMult': dict(group=_G2, title='Cieľ (× ATR)', inline='sl', tooltip=''),
    'useTimeClose': dict(group=_G2, title='Výstup v čase', inline='tc', tooltip='Predloha: po 8 min.'),
    'closeAfterMin': dict(group=_G2, title='Po (min)', inline='tc', tooltip=''),
    'fixedQty': dict(group=_G2, title='Pevný počet kontraktov', tooltip='Predloha: 6 kontraktov.'),
    'riskDollar': dict(group=_G2, title='Riziko na obchod ($)', tooltip=''),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
