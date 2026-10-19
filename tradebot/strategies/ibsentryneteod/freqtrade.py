"""IBS Entry Zone (C# jadro EOD) vo Freqtrade — adaptér nad C# jadrom, tie isté signály ako `IBSEntryNetStrategy` + koniec dňa 15:59 NY.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryNetEodStrategy.py`.
"""

from __future__ import annotations

from ..ibsentrynet.freqtrade import IBSEntryNetStrategy

#: `enter_tag` obchodu je ``ibsentryneteod:<…>``.
ENTRY_TAG_PREFIX = "ibsentryneteod:"

__all__ = ["IBSEntryNetEodStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryNetEodStrategy(IBSEntryNetStrategy):
    """IBS Entry Zone (C# jadro EOD) — signály predlohy, o 15:59 New York všetko zavreté."""

    STRATEGY_KEY = "ibsentryneteod"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
