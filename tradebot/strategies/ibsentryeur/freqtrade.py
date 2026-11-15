"""IBS EZ 6E vo Freqtrade — tie isté signály ako `IBSEntryZoneStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryEurStrategy.py`.
"""

from __future__ import annotations

from ..ibsentry.freqtrade import IBSEntryZoneStrategy

__all__ = ["IBSEntryEurStrategy"]


class IBSEntryEurStrategy(IBSEntryZoneStrategy):
    STRATEGY_KEY = "ibsentryeur"
    ENTRY_TAG_PREFIX = "ibsentryeur:"

    timeframe = "3m"
