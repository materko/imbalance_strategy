"""VWAP OP vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapOpStrategy.py`.
VWAP a HTF ATR si engine skladá z barov grafu sám a VWAP sa každý deň začína od nuly,
takže nepotrebuje informatívny TF ani seeding.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["VwapOpStrategy"]


class VwapOpStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "vwapop"
    ENTRY_TAG_PREFIX = "vwapop:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # `allowShort` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = bool(self.tb_cfg.allowShort) and self.config.get("trading_mode", "spot") != "spot"
