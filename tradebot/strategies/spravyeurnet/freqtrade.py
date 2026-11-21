"""SPRÁVY EUR/USD (C# jadro) vo Freqtrade — engine beží v C# cez most.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SpravyEurNetStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SpravyEurNetStrategy"]


class SpravyEurNetStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "spravyeurnet"
    ENTRY_TAG_PREFIX = "spravyeurnet:"

    timeframe = "5m"
