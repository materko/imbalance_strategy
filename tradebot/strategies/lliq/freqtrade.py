"""LONDON LIQUIDITY IFVG 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/LliqStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["LliqStrategy"]


class LliqStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "lliq"
    ENTRY_TAG_PREFIX = "lliq:"

    timeframe = "5m"
