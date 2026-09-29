"""JSS vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/JssStrategy.py`.
TF štruktúry si engine skladá z barov grafu sám (predhistóriu dostane seedom).
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["JssStrategy"]


class JssStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "jss"
    ENTRY_TAG_PREFIX = "jss:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
