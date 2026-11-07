"""VA NÁVRAT 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Va80Strategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["Va80Strategy"]


class Va80Strategy(TradebotStrategyBase):
    STRATEGY_KEY = "va80"
    ENTRY_TAG_PREFIX = "va80:"

    timeframe = "1m"
