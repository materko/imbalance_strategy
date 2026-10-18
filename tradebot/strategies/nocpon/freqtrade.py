"""NOC + PONDELOK vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NocPonStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["NocPonStrategy"]


class NocPonStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "nocpon"
    ENTRY_TAG_PREFIX = "nocpon:"

    timeframe = "5m"
