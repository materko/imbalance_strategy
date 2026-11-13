"""NOA 1.0 (BTC) vo Freqtrade — tie isté signály ako `NoaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaBtcStrategy.py`.
"""

from __future__ import annotations

from ..noa.freqtrade import NoaStrategy

__all__ = ["NoaBtcStrategy"]


class NoaBtcStrategy(NoaStrategy):
    STRATEGY_KEY = "noabtc"
    ENTRY_TAG_PREFIX = "noabtc:"

    timeframe = "5m"
