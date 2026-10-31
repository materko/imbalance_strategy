"""WILLIAMS %R LONG 1.0 (MGC) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprMgcStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprMgcStrategy"]


class WprMgcStrategy(WprStrategy):
    STRATEGY_KEY = "wprmgc"
    ENTRY_TAG_PREFIX = "wprmgc:"

    timeframe = "15m"
