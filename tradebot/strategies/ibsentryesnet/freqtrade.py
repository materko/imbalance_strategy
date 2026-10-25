"""IBS EZ ES (C# jadro) vo Freqtrade — tie isté signály ako `IBSEntryNetStrategy`, profil pre ES.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IBSEntryEsNetStrategy.py`.
"""

from __future__ import annotations

from ..ibsentrynet.freqtrade import IBSEntryNetStrategy

ENTRY_TAG_PREFIX = "ibsentryesnet:"

__all__ = ["IBSEntryEsNetStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryEsNetStrategy(IBSEntryNetStrategy):
    STRATEGY_KEY = "ibsentryesnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX
