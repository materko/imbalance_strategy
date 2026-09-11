"""Divergenčná stratégia vo Freqtrade — nad generickým adaptérom smer obchodov a trailing.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/DivergenceStrategy.py`.

Trailing je to jediné, čo generická báza nerobí sama (Freqtrade dostáva stop cez
`custom_stoploss`, nie z plánu). Postup je ten istý ako v IBS (`tradebot/strategies/ibs/freqtrade.py`):
extrém od vstupu, poradie extrémov v sviečke (`extreme_before_stop`), spiatočná noha
proti `close` 1m detailu — len trailing plán je dvojstupňový (`TwoStageTrailing`).
"""

from __future__ import annotations

import logging

from tradebot.adapters.freqtrade.base import TradebotStrategyBase
from tradebot.core.risk import extreme_before_stop
from tradebot.core.types import Direction, TradeDirection

from .trailing import TwoStageTrailing

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

    def _trailing_stop(self, pair: str, trade, base_stop: float) -> float:
        if not self.tb_cfg.enableTrailing:
            return base_stop
        row = self._trade_signal(pair, trade)
        if row is None or row.entry != row.entry:
            return base_stop
        trail = TwoStageTrailing.from_config(self.tb_cfg, self.tb_inst, row.entry)
        if trail is None:
            return base_stop

        long = not trade.is_short
        direction = Direction.LONG if long else Direction.SHORT
        key = (pair, trade.open_date_utc)
        prev = self._extremes.get(key, row.entry)

        bar_open, high, low = getattr(self, "_candle", (None, None, None))
        if high is None or low is None:
            extreme = trade.min_rate if trade.is_short else trade.max_rate
            return trail.stop_price(direction, row.entry, base_stop, extreme or row.entry)

        best = high if long else low
        after = max(prev, best) if long else min(prev, best)
        self._extremes[key] = after
        before_stop = trail.stop_price(direction, row.entry, base_stop, prev)
        after_stop = trail.stop_price(direction, row.entry, base_stop, after)

        if extreme_before_stop(bar_open, high, low, long=long):
            return after_stop
        if (low <= before_stop) if long else (high >= before_stop):
            return before_stop
        close = self._detail_close(pair, self._candle_time)
        if close is None:
            return after_stop
        crossed = close <= after_stop if long else close >= after_stop
        return after_stop if crossed else before_stop
