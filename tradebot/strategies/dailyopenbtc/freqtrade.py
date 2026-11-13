"""DAILY OPEN 1.0 (BTC) vo Freqtrade — tie isté signály ako `DailyOpenStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/DailyOpenBtcStrategy.py`.
"""

from __future__ import annotations

from ..dailyopen.freqtrade import DailyOpenStrategy

__all__ = ["DailyOpenBtcStrategy"]


class DailyOpenBtcStrategy(DailyOpenStrategy):
    STRATEGY_KEY = "dailyopenbtc"
    ENTRY_TAG_PREFIX = "dailyopenbtc:"

    timeframe = "1h"
