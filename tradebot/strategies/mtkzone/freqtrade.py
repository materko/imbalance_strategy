"""MTK ZONE vo Freqtrade — nad generickým adaptérom nič navyše."""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["MtkZoneStrategy"]


class MtkZoneStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "mtkzone"
    ENTRY_TAG_PREFIX = "mz:"

    timeframe = "3m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
