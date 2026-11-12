"""NOA 1.0 MYM (C# jadro) vo Freqtrade.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaMymNetStrategy.py`.
"""

from __future__ import annotations

from ..noamym.freqtrade import NoaMymStrategy

__all__ = ["NoaMymNetStrategy"]


class NoaMymNetStrategy(NoaMymStrategy):
    STRATEGY_KEY = "noamymnet"
    ENTRY_TAG_PREFIX = "noamymnet:"

    timeframe = "5m"
