"""WILLIAMS %R LONG 1.0 (C# jadro) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprNetStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprNetStrategy"]


class WprNetStrategy(WprStrategy):
    STRATEGY_KEY = "wprnet"
    ENTRY_TAG_PREFIX = "wprnet:"

    timeframe = "15m"
