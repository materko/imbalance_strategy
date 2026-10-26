"""SD ZÓNY EURUSD (C# jadro) vo Freqtrade — engine beží v C# cez most.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SdEurNetStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SdEurNetStrategy"]


class SdEurNetStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "sdeurnet"
    ENTRY_TAG_PREFIX = "sdeurnet:"

    timeframe = "5m"
