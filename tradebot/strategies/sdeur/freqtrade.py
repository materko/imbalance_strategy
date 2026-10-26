"""SD ZÓNY EURUSD vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SdEurStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SdEurStrategy"]


class SdEurStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "sdeur"
    ENTRY_TAG_PREFIX = "sdeur:"

    timeframe = "5m"
