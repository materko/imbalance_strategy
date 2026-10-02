"""CRT + TBS vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/CrtStrategy.py`.
TF rangu si engine skladá z barov grafu sám (predhistóriu dostane seedom).
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["CrtStrategy"]


class CrtStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "crt"
    ENTRY_TAG_PREFIX = "crt:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
