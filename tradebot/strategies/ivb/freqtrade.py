"""IVB vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IvbStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["IvbStrategy"]


class IvbStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "ivb"
    ENTRY_TAG_PREFIX = "ivb:"

    timeframe = "5m"
