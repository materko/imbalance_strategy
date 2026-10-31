"""FLASH TRIGGER ORB 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FlashorbStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["FlashorbStrategy"]


class FlashorbStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "flashorb"
    ENTRY_TAG_PREFIX = "flashorb:"

    timeframe = "15m"
