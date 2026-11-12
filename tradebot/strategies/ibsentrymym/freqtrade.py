"""IBS EZ MYM vo Freqtrade — tie isté signály ako `IBSEntryZoneStrategy`, profily pre MYM v ATR.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryMymStrategy.py`.
"""

from __future__ import annotations

from ..ibsentry.freqtrade import IBSEntryZoneStrategy

#: `enter_tag` obchodu je ``ibsentrymym:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsentrymym:"

__all__ = ["IBSEntryMymStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryMymStrategy(IBSEntryZoneStrategy):
    """IBS Entry Zone na Micro E-mini Dow futures (MYM)."""

    STRATEGY_KEY = "ibsentrymym"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
