"""IVB 1.0 (MGC) vo Freqtrade — tie isté signály ako `IvbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IvbMgcStrategy.py`.
"""

from __future__ import annotations

from ..ivb.freqtrade import IvbStrategy

__all__ = ["IvbMgcStrategy"]


class IvbMgcStrategy(IvbStrategy):
    STRATEGY_KEY = "ivbmgc"
    ENTRY_TAG_PREFIX = "ivbmgc:"

    timeframe = "5m"
