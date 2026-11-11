"""NOA 1.0 MGC (C# jadro) vo Freqtrade.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaMgcNetStrategy.py`.
"""

from __future__ import annotations

from ..noamgc.freqtrade import NoaMgcStrategy

__all__ = ["NoaMgcNetStrategy"]


class NoaMgcNetStrategy(NoaMgcStrategy):
    STRATEGY_KEY = "noamgcnet"
    ENTRY_TAG_PREFIX = "noamgcnet:"

    timeframe = "5m"
