"""WILLIAMS %R LONG 1.0 (ES) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprEsStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprEsStrategy"]


class WprEsStrategy(WprStrategy):
    STRATEGY_KEY = "wpres"
    ENTRY_TAG_PREFIX = "wpres:"

    timeframe = "15m"
