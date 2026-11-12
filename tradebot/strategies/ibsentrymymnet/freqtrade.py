"""IBS EZ MYM (C# jadro) vo Freqtrade — tie isté signály ako `IBSEntryNetStrategy`, profil pre MYM.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryMymNetStrategy.py`.
"""

from __future__ import annotations

from ..ibsentrynet.freqtrade import IBSEntryNetStrategy

ENTRY_TAG_PREFIX = "ibsentrymymnet:"

__all__ = ["IBSEntryMymNetStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryMymNetStrategy(IBSEntryNetStrategy):
    STRATEGY_KEY = "ibsentrymymnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX
