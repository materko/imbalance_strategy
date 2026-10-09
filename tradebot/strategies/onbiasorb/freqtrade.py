"""Overnight Bias ORB vo Freqtrade — long aj short."""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["OnBiasOrbStrategy"]


class OnBiasOrbStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "onbiasorb"
    ENTRY_TAG_PREFIX = "onbiasorb:"

    timeframe = "15m"

    def _after_profile(self) -> None:
        # shorty vyžadujú futures trading mode
        self.can_short = self.config.get("trading_mode", "spot") != "spot"
