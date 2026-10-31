"""ORB 15/5 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Orb15Strategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["Orb15Strategy"]


class Orb15Strategy(TradebotStrategyBase):
    STRATEGY_KEY = "orb15"
    ENTRY_TAG_PREFIX = "orb15:"

    timeframe = "5m"
