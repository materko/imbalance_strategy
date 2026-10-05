"""Volume Profile POC vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SvpStrategy.py`.
Profil sa počíta z barov grafu.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["SvpStrategy"]


class SvpStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "svp"
    ENTRY_TAG_PREFIX = "svp:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
