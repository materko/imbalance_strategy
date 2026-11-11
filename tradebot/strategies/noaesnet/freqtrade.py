"""NOA 1.0 ES (C# jadro) vo Freqtrade.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaEsNetStrategy.py`.
"""

from __future__ import annotations

from ..noaes.freqtrade import NoaEsStrategy

__all__ = ["NoaEsNetStrategy"]


class NoaEsNetStrategy(NoaEsStrategy):
    STRATEGY_KEY = "noaesnet"
    ENTRY_TAG_PREFIX = "noaesnet:"

    timeframe = "5m"
