"""Drift VWAP vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapDriftStrategy.py`.
15m sviečky VWAP si engine skladá z barov grafu sám a VWAP sa každý deň začína od nuly,
takže nepotrebuje informatívny TF ani seeding.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["VwapDriftStrategy"]


class VwapDriftStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "vwapdrift"
    ENTRY_TAG_PREFIX = "vwapdrift:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # `tradeDirection` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = bool(self.tb_cfg.allow_short) and self.config.get("trading_mode", "spot") != "spot"
