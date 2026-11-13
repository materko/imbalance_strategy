"""SWEEPING ENGULF 1.0 (BTC) vo Freqtrade — tie isté signály ako `SweepEngulfStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SweepEngulfBtcStrategy.py`.
"""

from __future__ import annotations

from ..sweepengulf.freqtrade import SweepEngulfStrategy

__all__ = ["SweepEngulfBtcStrategy"]


class SweepEngulfBtcStrategy(SweepEngulfStrategy):
    STRATEGY_KEY = "sweepengulfbtc"
    ENTRY_TAG_PREFIX = "sweepengulfbtc:"

    timeframe = "4h"
