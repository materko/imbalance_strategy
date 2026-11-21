"""IB RETRACE 1.0 (MYM) vo Freqtrade — tie isté signály ako `IbRetStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetMymStrategy.py`.
"""

from __future__ import annotations

from ..ibret.freqtrade import IbRetStrategy

__all__ = ["IbRetMymStrategy"]


class IbRetMymStrategy(IbRetStrategy):
    STRATEGY_KEY = "ibretmym"
    ENTRY_TAG_PREFIX = "ibretmym:"

    timeframe = "5m"
