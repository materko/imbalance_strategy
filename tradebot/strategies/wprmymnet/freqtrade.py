"""WILLIAMS %R LONG 1.0 MYM (C# jadro) vo Freqtrade — tie isté signály ako `WprStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprMymNetStrategy.py`.
"""

from __future__ import annotations

from ..wpr.freqtrade import WprStrategy

__all__ = ["WprMymNetStrategy"]


class WprMymNetStrategy(WprStrategy):
    STRATEGY_KEY = "wprmymnet"
    ENTRY_TAG_PREFIX = "wprmymnet:"

    timeframe = "15m"
