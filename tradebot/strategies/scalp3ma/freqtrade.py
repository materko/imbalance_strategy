"""Scalping 3MA + RSI + fraktál vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Scalp3MaStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["Scalp3MaStrategy"]


class Scalp3MaStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "scalp3ma"
    ENTRY_TAG_PREFIX = "scalp3ma:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
