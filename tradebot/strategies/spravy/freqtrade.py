"""SPRÁVY vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SpravyStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SpravyStrategy"]


class SpravyStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "spravy"
    ENTRY_TAG_PREFIX = "spravy:"

    timeframe = "5m"
