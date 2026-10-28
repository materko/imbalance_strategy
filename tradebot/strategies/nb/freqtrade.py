"""NB vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NbStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["NbStrategy"]


class NbStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "nb"
    ENTRY_TAG_PREFIX = "nb:"

    timeframe = "15m"
