"""TKS 1.0 (MGC) vo Freqtrade — tie isté signály ako `TksStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksMgcStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

__all__ = ["TksMgcStrategy"]


class TksMgcStrategy(TksStrategy):
    STRATEGY_KEY = "tksmgc"
    ENTRY_TAG_PREFIX = "tksmgc:"

    timeframe = "3m"
