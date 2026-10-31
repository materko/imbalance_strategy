"""ORB 15/5 1.0 (ES) vo Freqtrade — tie isté signály ako `Orb15Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Orb15EsStrategy.py`.
"""

from __future__ import annotations

from ..orb15.freqtrade import Orb15Strategy

__all__ = ["Orb15EsStrategy"]


class Orb15EsStrategy(Orb15Strategy):
    STRATEGY_KEY = "orb15es"
    ENTRY_TAG_PREFIX = "orb15es:"

    timeframe = "5m"
