"""Craig Percoco 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/PercocoStrategy.py`.
15m sa skladá z barov grafu.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["PercocoStrategy"]


class PercocoStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "percoco"
    ENTRY_TAG_PREFIX = "pc:"

    timeframe = "1m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
