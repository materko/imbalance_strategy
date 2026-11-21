"""IB RETRACE 1.0 vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["IbRetStrategy"]


class IbRetStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "ibret"
    ENTRY_TAG_PREFIX = "ibret:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
