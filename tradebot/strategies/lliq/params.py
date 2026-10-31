"""Popisy parametrov LONDON LIQUIDITY IFVG 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '🕘 Seansa a sweep (New York, HHMM)'
_G1 = '🛡️ Stop a cieľ'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'sessionStart': dict(group=_G0, title='Seansa od', inline='s', tooltip='Predloha: 13:00.'),
    'sessionEnd': dict(group=_G0, title='do', inline='s', tooltip='Predloha: 19:00.'),
    'lsStart': dict(group=_G0, title='Sweep od', inline='ls', tooltip=''),
    'lsEnd': dict(group=_G0, title='do', inline='ls', tooltip=''),
    'maxIfvgAgeHours': dict(group=_G0, title='FVG najstaršie (h)', tooltip=''),
    'useDayFilter': dict(group=_G0, title='Filter dní', tooltip=''),
    'tradeMon': dict(group=_G0, title='Po', inline='d', tooltip=''),
    'tradeTue': dict(group=_G0, title='Ut', inline='d', tooltip=''),
    'tradeWed': dict(group=_G0, title='St', inline='d', tooltip=''),
    'tradeThu': dict(group=_G0, title='Št', inline='d', tooltip=''),
    'tradeFri': dict(group=_G0, title='Pi', inline='d', tooltip=''),
    'swingLookback': dict(group=_G1, title='Swing z barov', tooltip=''),
    'slType': dict(group=_G1, title='Stop', tooltip='0 = swing, 1 = ATR.'),
    'tpType': dict(group=_G1, title='Cieľ', tooltip='0 = range seansy, 1 = RR, 2 = ATR.'),
    'riskReward': dict(group=_G1, title='RR', tooltip=''),
    'atrLength': dict(group=_G1, title='ATR', tooltip=''),
    'slAtrMult': dict(group=_G1, title='Stop (× ATR)', inline='m', tooltip=''),
    'tpAtrMult': dict(group=_G1, title='Cieľ (× ATR)', inline='m', tooltip=''),
    'fixedQty': dict(group=_G1, title='Pevný počet kontraktov', tooltip='Predloha: 1 lot.'),
    'riskDollar': dict(group=_G1, title='Riziko na obchod ($)', tooltip='Predloha: 100 $.'),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
