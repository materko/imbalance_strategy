"""TKS 1.0 (MYM) vo Freqtrade — tie isté signály ako `TksStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksMymStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

__all__ = ["TksMymStrategy"]


class TksMymStrategy(TksStrategy):
    STRATEGY_KEY = "tksmym"
    ENTRY_TAG_PREFIX = "tksmym:"

    timeframe = "3m"
