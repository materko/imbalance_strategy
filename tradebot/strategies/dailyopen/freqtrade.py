"""DAILY OPEN vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/DailyOpenStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["DailyOpenStrategy"]


class DailyOpenStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "dailyopen"
    ENTRY_TAG_PREFIX = "dailyopen:"

    timeframe = "1h"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
