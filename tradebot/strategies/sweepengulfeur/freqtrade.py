"""SWEEPING ENGULF 1.0 (6E) vo Freqtrade — tie isté signály ako `SweepEngulfStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SweepEngulfEurStrategy.py`.
"""

from __future__ import annotations

from ..sweepengulf.freqtrade import SweepEngulfStrategy

__all__ = ["SweepEngulfEurStrategy"]


class SweepEngulfEurStrategy(SweepEngulfStrategy):
    STRATEGY_KEY = "sweepengulfeur"
    ENTRY_TAG_PREFIX = "sweepengulfeur:"

    timeframe = "4h"
