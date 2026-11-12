"""SWEEPING ENGULF 1.0 (MYM) vo Freqtrade — tie isté signály ako `SweepEngulfStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SweepEngulfMymStrategy.py`.
"""

from __future__ import annotations

from ..sweepengulf.freqtrade import SweepEngulfStrategy

__all__ = ["SweepEngulfMymStrategy"]


class SweepEngulfMymStrategy(SweepEngulfStrategy):
    STRATEGY_KEY = "sweepengulfmym"
    ENTRY_TAG_PREFIX = "sweepengulfmym:"

    timeframe = "4h"
