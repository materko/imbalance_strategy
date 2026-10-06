"""Mag7 + SPX sila vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Mag7Strategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["Mag7Strategy"]


class Mag7Strategy(TradebotStrategyBase):
    STRATEGY_KEY = "mag7"
    ENTRY_TAG_PREFIX = "mag7:"

    timeframe = "15m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allowS) and self.config.get("trading_mode", "spot") != "spot"
