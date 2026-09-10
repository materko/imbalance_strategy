"""Gap Fill vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/GapStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["GapStrategy"]


class GapStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "gap"
    ENTRY_TAG_PREFIX = "gap:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # Gap up sa obchoduje na short, takze shorty su potrebne vzdy okrem "Gap down only".
        self.can_short = (bool(self.tb_cfg.trade_gap_up)
                          and self.config.get("trading_mode", "spot") != "spot")
