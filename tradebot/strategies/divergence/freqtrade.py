"""Divergenčná stratégia vo Freqtrade — nad generickým adaptérom len smer obchodov.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/DivergenceStrategy.py`.

Dvojstupňový trailing (`TwoStageTrailing`) je v pláne obchodu a uplatní ho generická
báza (`TradebotStrategyBase._trailing_stop`) — `stop_price` je polymorfný.
"""

from __future__ import annotations

import logging

from tradebot.adapters.freqtrade.base import TradebotStrategyBase
from tradebot.core.types import TradeDirection

logger = logging.getLogger(__name__)

__all__ = ["DivergenceStrategy"]


class DivergenceStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "divergence"
    ENTRY_TAG_PREFIX = "div:"

    timeframe = "15m"

    def _after_profile(self) -> None:
        allows_short = self.tb_cfg.tradeDirection is not TradeDirection.LONG_ONLY
        self.can_short = allows_short and self.config.get("trading_mode", "spot") != "spot"
        if allows_short and not self.can_short:
            logger.warning("divergence: spotový trh — tradeDirection %s sa zužuje na longy",
                           self.tb_cfg.tradeDirection.value)
