"""Range Breakout vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/RangeStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["RangeStrategy"]


class RangeStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "range"
    ENTRY_TAG_PREFIX = "range:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # `tradeDirection` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
