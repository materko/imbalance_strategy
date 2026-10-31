"""WILLIAMS %R LONG 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/WprStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["WprStrategy"]


class WprStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "wpr"
    ENTRY_TAG_PREFIX = "wpr:"

    timeframe = "15m"
