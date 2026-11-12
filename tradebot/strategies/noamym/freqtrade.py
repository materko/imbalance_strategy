"""NOA 1.0 (MYM) vo Freqtrade — tie isté signály ako `NoaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaMymStrategy.py`.
"""

from __future__ import annotations

from ..noa.freqtrade import NoaStrategy

__all__ = ["NoaMymStrategy"]


class NoaMymStrategy(NoaStrategy):
    STRATEGY_KEY = "noamym"
    ENTRY_TAG_PREFIX = "noamym:"

    timeframe = "5m"
