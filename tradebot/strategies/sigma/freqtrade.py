"""SIGMA BREAKOUT 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SigmaStrategy"]


class SigmaStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "sigma"
    ENTRY_TAG_PREFIX = "sigma:"

    timeframe = "5m"
