"""WILLIAMS %R LONG 1.0 (MYM) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprMymStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprMymStrategy"]


class WprMymStrategy(WprStrategy):
    STRATEGY_KEY = "wprmym"
    ENTRY_TAG_PREFIX = "wprmym:"

    timeframe = "15m"
