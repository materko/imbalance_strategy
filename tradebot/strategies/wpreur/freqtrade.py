"""WILLIAMS %R LONG 1.0 (6E) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprEurStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprEurStrategy"]


class WprEurStrategy(WprStrategy):
    STRATEGY_KEY = "wpreur"
    ENTRY_TAG_PREFIX = "wpreur:"

    timeframe = "15m"
