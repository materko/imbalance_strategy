"""MTK EMAS vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkEmasStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["MtkEmasStrategy"]


class MtkEmasStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "mtkemas"
    ENTRY_TAG_PREFIX = "mtkemas:"

    timeframe = "4h"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
