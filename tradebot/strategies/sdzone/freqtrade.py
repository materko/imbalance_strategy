"""SD Zones vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SDZoneStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SDZoneStrategy"]


class SDZoneStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "sdzone"
    ENTRY_TAG_PREFIX = "sdzone:"

    timeframe = "15m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
