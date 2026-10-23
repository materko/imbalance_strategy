"""NY VA BREAKOUT vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NyVaStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["NyVaStrategy"]


class NyVaStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "nyva"
    ENTRY_TAG_PREFIX = "nyva:"

    timeframe = "3m"
