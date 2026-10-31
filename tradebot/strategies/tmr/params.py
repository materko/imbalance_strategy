"""Popisy parametrov T-MEAN REVERSION 1.0 pre formulár webapp."""

from __future__ import annotations

from typing import Any

from tradebot.core.entry_confirm import entry_confirm_params
from tradebot.core.entry_filter import entry_filter_params
from tradebot.core.entry_order import entry_order_params

__all__ = ["GROUPS", "PARAMS"]

_G0 = '📅 Vstup a výstup (UTC, 1 = pondelok)'
_G1 = '🛡️ Poistka a veľkosť'
_GP = "🧩 Rozšírenia portu"
_GE = "🧾 Typ vstupu (market / limit)"

GROUPS: tuple[str, ...] = (_G0, _G1, _GP, _GE)

PARAMS: dict[str, dict[str, Any]] = {
    'entryDay': dict(group=_G0, title='Deň vstupu', inline='en', tooltip='1 = pondelok … 7 = nedeľa.'),
    'entryHour': dict(group=_G0, title='Hodina', inline='en', tooltip='UTC.'),
    'entryMinute': dict(group=_G0, title='Minúta od', inline='en', tooltip='Prvý bar tej hodiny s minútou aspoň takou.'),
    'exitDay': dict(group=_G0, title='Deň výstupu', inline='ex', tooltip='Predloha: 3 = streda.'),
    'exitHour': dict(group=_G0, title='Hodina', inline='ex', tooltip='UTC.'),
    'exitMinute': dict(group=_G0, title='Minúta od', inline='ex', tooltip=''),
    'requireRedFriday': dict(group=_G0, title='Len po červenom piatku', tooltip='Predloha: vždy zapnuté.'),
    'checkMarketHours': dict(group=_G0, title='Len v hodinách trhu', inline='mh', tooltip='Mimo nich bar nič nerobí.'),
    'marketOpenHour': dict(group=_G0, title='Od (UTC)', inline='mh', tooltip=''),
    'marketCloseHour': dict(group=_G0, title='Do (UTC)', inline='mh', tooltip=''),
    'stopPct': dict(group=_G1, title='Stop (% od vstupu)', tooltip='Predloha bez stopu; 0 = poistka 10 %.'),
    'fixedQty': dict(group=_G1, title='Pevný počet kontraktov', tooltip='Predloha: pevný počet (1).'),
    'riskDollar': dict(group=_G1, title='Riziko na obchod ($)', tooltip='Pri vypnutom pevnom počte: riziko po stop.'),
    "leverage": dict(group=_GP, title="Páka", tooltip="Páka pre Freqtrade futures."),
}
PARAMS.update(entry_order_params(_GE))
PARAMS.update(entry_confirm_params(_GE))
PARAMS.update(entry_filter_params(_GE))
