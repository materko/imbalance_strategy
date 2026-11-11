"""NOA 1.0 (ES) vo Freqtrade — tie isté signály ako `NoaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaEsStrategy.py`.
"""

from __future__ import annotations

from ..noa.freqtrade import NoaStrategy

__all__ = ["NoaEsStrategy"]


class NoaEsStrategy(NoaStrategy):
    STRATEGY_KEY = "noaes"
    ENTRY_TAG_PREFIX = "noaes:"

    timeframe = "5m"
