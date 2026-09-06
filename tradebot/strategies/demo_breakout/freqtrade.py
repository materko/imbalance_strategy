"""Demo Donchian Breakout vo Freqtrade — nad generickým adaptérom nič navyše.

Shim pre resolver: `platforms/freqtrade/user_data/strategies/DemoBreakoutStrategy.py`.
"""

from __future__ import annotations

from tradebot.adapters.freqtrade.base import TradebotStrategyBase

__all__ = ["DemoBreakoutStrategy"]


class DemoBreakoutStrategy(TradebotStrategyBase):
    STRATEGY_KEY = "demo_breakout"
    ENTRY_TAG_PREFIX = "demo:"

    timeframe = "5m"

    def _after_profile(self) -> None:
        # Pine `allowShort` -> Freqtrade `can_short` (shorty vyžadujú futures trading mode).
        self.can_short = bool(self.tb_cfg.allowShort)
