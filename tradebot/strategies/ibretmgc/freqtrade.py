"""IB RETRACE 1.0 (MGC) vo Freqtrade — tie isté signály ako `IbRetStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetMgcStrategy.py`.
"""

from __future__ import annotations

from ..ibret.freqtrade import IbRetStrategy

__all__ = ["IbRetMgcStrategy"]


class IbRetMgcStrategy(IbRetStrategy):
    STRATEGY_KEY = "ibretmgc"
    ENTRY_TAG_PREFIX = "ibretmgc:"

    timeframe = "5m"
