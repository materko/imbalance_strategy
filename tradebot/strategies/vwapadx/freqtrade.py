"""VWAP ADX vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapAdxStrategy.py`. Len long.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["VwapAdxStrategy"]


class VwapAdxStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "vwapadx"
    ENTRY_TAG_PREFIX = "vwapadx:"

    timeframe = "1m"
