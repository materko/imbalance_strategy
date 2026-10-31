"""Popisy parametrov SIGMA BREAKOUT 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '📊 Pásmo'
_G1 = '🛡️ Stop a veľkosť'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'nSigmaDays': dict(group=_G0, title='Dní do priemeru', tooltip='Predloha: 14.'),
    'bandMult': dict(group=_G0, title='Násobok sigma', tooltip='Predloha: 1.'),
    'useVwap': dict(group=_G0, title='Referencia VWAP', tooltip='Vypnuté = open RTH (predloha).'),
    'slPct': dict(group=_G1, title='Stop (% od vstupu)', tooltip='Predloha: 0 = bez stopu (tu poistka 10 %).'),
    'useCloseAtEnd': dict(group=_G1, title='Zavrieť o 16:00 NY', tooltip='Predloha: vždy.'),
    'fixedQty': dict(group=_G1, title='Pevný počet kontraktov', tooltip='Predloha: bez stopu 1 kontrakt.'),
    'riskDollar': dict(group=_G1, title='Riziko na obchod ($)', tooltip='Pri stope a vypnutom pevnom počte.'),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
