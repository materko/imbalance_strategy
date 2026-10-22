"""IBS EZ ES vo Freqtrade — tie isté signály ako `IBSEntryZoneStrategy`, profily pre ES v ATR.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryEsStrategy.py`.
"""

from __future__ import annotations

from ..ibsentry.freqtrade import IBSEntryZoneStrategy

#: `enter_tag` obchodu je ``ibsentryes:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsentryes:"

__all__ = ["IBSEntryEsStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryEsStrategy(IBSEntryZoneStrategy):
    """IBS Entry Zone na S&P 500 futures (ES)."""

    STRATEGY_KEY = "ibsentryes"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
