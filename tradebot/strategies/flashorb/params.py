"""Popisy parametrov FLASH TRIGGER ORB 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '🕯️ Vybraná sviečka'
_G1 = '🛡️ Stop, cieľ a koniec dňa'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'targetHour': dict(group=_G0, title='Hodina', inline='tg', tooltip='Predloha: 14:30 UTC = 9:30 NY v zime.'),
    'targetMinute': dict(group=_G0, title='Minúta', inline='tg', tooltip=''),
    'utcOffset': dict(group=_G0, title='Posun od UTC (h)', tooltip='Pevný posun; letný čas nerieši (predloha).'),
    'dayFilter': dict(group=_G0, title='Filter dní', tooltip=''),
    'tradeMonday': dict(group=_G0, title='Po', inline='d', tooltip=''),
    'tradeTuesday': dict(group=_G0, title='Ut', inline='d', tooltip=''),
    'tradeWednesday': dict(group=_G0, title='St', inline='d', tooltip=''),
    'tradeThursday': dict(group=_G0, title='Št', inline='d', tooltip=''),
    'tradeFriday': dict(group=_G0, title='Pi', inline='d', tooltip=''),
    'riskReward': dict(group=_G1, title='RR', tooltip='Predloha: 3.'),
    'activateTrailing': dict(group=_G1, title='Trailing', inline='tr', tooltip='Predloha: vypnuté.'),
    'trailActivatePoints': dict(group=_G1, title='Od zisku (body)', inline='tr', tooltip=''),
    'trailBufferPoints': dict(group=_G1, title='Odstup (body)', inline='tr', tooltip=''),
    'useEodClose': dict(group=_G1, title='Zavrieť na konci dňa', inline='eod', tooltip='Predloha: 23:59 UTC.'),
    'eodHour': dict(group=_G1, title='Hodina (UTC)', inline='eod', tooltip=''),
    'eodMinute': dict(group=_G1, title='Minúta', inline='eod', tooltip=''),
    'riskDollar': dict(group=_G1, title='Riziko na obchod ($)', tooltip='Predloha: 100 $ pri režime pevného rizika.'),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
