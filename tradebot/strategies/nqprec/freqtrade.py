"""NQ PRECISION 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NqprecStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["NqprecStrategy"]


class NqprecStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "nqprec"
    ENTRY_TAG_PREFIX = "nqprec:"

    timeframe = "1m"
