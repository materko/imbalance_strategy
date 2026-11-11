"""NOA 1.0 (MGC) vo Freqtrade — tie isté signály ako `NoaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaMgcStrategy.py`.
"""

from __future__ import annotations

from ..noa.freqtrade import NoaStrategy

__all__ = ["NoaMgcStrategy"]


class NoaMgcStrategy(NoaStrategy):
    STRATEGY_KEY = "noamgc"
    ENTRY_TAG_PREFIX = "noamgc:"

    timeframe = "5m"
