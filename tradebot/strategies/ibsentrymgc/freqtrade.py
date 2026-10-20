"""IBS EZ MGC vo Freqtrade — tie isté signály ako `IBSEntryZoneStrategy`, profily pre zlato v ATR.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryMgcStrategy.py`.
"""

from __future__ import annotations

from ..ibsentry.freqtrade import IBSEntryZoneStrategy

#: `enter_tag` obchodu je ``ibsentrymgc:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsentrymgc:"

__all__ = ["IBSEntryMgcStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryMgcStrategy(IBSEntryZoneStrategy):
    """IBS Entry Zone na zlate (MGC)."""

    STRATEGY_KEY = "ibsentrymgc"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
