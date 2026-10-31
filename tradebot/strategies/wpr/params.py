"""Popisy parametrov WILLIAMS %R LONG 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '📉 Williams %R'
_G1 = '🛡️ Poistka a veľkosť'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'wprLen': dict(group=_G0, title='Perióda', tooltip='Predloha: 14.'),
    'entryLevel': dict(group=_G0, title='Vstup pod', inline='lv', tooltip='Predloha: −90.'),
    'exitLevel': dict(group=_G0, title='Výstup od', inline='lv', tooltip='Predloha: −30.'),
    'exitMode': dict(group=_G0, title='Výstup', tooltip='0 = nad high predošlej sviečky, 1 = %R, 2 = oboje.'),
    'stopPct': dict(group=_G1, title='Stop (% od vstupu)', tooltip='Predloha bez stopu; 0 = poistka 10 %.'),
    'fixedQty': dict(group=_G1, title='Pevný počet kontraktov', tooltip='Predloha: 1 kontrakt.'),
    'riskDollar': dict(group=_G1, title='Riziko na obchod ($)', tooltip='Pri vypnutom pevnom počte.'),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
