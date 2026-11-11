"""MTK ORB (MGC) vo Freqtrade — tie isté signály ako `Orb15Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkOrbStrategy.py`.
"""

from __future__ import annotations

from ..orb15.freqtrade import Orb15Strategy

__all__ = ["MtkOrbStrategy"]


class MtkOrbStrategy(Orb15Strategy):
    STRATEGY_KEY = "mtkorb"
    ENTRY_TAG_PREFIX = "mtkorb:"

    timeframe = "5m"
