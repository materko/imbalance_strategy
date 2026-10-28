"""M2 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/M2Strategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["M2Strategy"]


class M2Strategy(TradebotStrategyBase):
    STRATEGY_KEY = "m2"
    ENTRY_TAG_PREFIX = "m2:"

    timeframe = "1m"
