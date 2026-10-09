"""Volt Break vo Freqtrade — nad generickým adaptérom nič navyše. Len long."""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["VoltBreakStrategy"]


class VoltBreakStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "voltbreak"
    ENTRY_TAG_PREFIX = "voltbreak:"

    timeframe = "30m"
