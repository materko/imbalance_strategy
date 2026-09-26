"""Trendline Breakout vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TrendlineStrategy.py`.
Vyšší TF trendoviek si engine skladá z barov grafu sám (predhistóriu dostane seedom).
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["TrendlineStrategy"]


class TrendlineStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "trendlines"
    ENTRY_TAG_PREFIX = "trendlines:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # `tradeDirection` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
