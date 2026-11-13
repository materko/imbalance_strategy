"""Range Breakout (BTC) vo Freqtrade — tie isté signály ako `RangeStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/RangeBtcStrategy.py`.
"""

from __future__ import annotations

from ..range.freqtrade import RangeStrategy

__all__ = ["RangeBtcStrategy"]


class RangeBtcStrategy(RangeStrategy):
    STRATEGY_KEY = "rangebtc"
    ENTRY_TAG_PREFIX = "rangebtc:"

    timeframe = "3m"
