"""SPRÁVY (C# jadro) vo Freqtrade — engine beží v C# cez most.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SpravyNetStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SpravyNetStrategy"]


class SpravyNetStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "spravynet"
    ENTRY_TAG_PREFIX = "spravynet:"

    timeframe = "5m"
