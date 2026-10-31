"""ORB 15/5 1.0 (MGC) vo Freqtrade — tie isté signály ako `Orb15Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Orb15MgcStrategy.py`.
"""

from __future__ import annotations

from ..orb15.freqtrade import Orb15Strategy

__all__ = ["Orb15MgcStrategy"]


class Orb15MgcStrategy(Orb15Strategy):
    STRATEGY_KEY = "orb15mgc"
    ENTRY_TAG_PREFIX = "orb15mgc:"

    timeframe = "5m"
