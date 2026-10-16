"""NOA 1.0 vo Freqtrade — nad generickým adaptérom nič navyše."""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["NoaStrategy"]


class NoaStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "noa"
    ENTRY_TAG_PREFIX = "noa:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
