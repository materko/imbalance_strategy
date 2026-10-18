"""TKS 1.0 vo Freqtrade — nad generickým adaptérom nič navyše."""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["TksStrategy"]


class TksStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "tks"
    ENTRY_TAG_PREFIX = "tks:"

    timeframe = "3m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
