"""Market Structure vo Freqtrade — nad generickým adaptérom len smer obchodov.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/StructureStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase
from tradebot.core.types import TradeDirection

__all__ = ["StructureStrategy"]


class StructureStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "structure"
    ENTRY_TAG_PREFIX = "struct:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # Pine `tradeDirection` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        allows_short = self.tb_cfg.tradeDirection is not TradeDirection.LONG_ONLY
        self.can_short = allows_short and self.config.get("trading_mode", "spot") != "spot"
