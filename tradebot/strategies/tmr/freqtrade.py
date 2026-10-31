"""T-MEAN REVERSION 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TmrStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["TmrStrategy"]


class TmrStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "tmr"
    ENTRY_TAG_PREFIX = "tmr:"

    timeframe = "15m"
