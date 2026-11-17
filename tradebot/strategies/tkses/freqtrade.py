"""TKS 1.0 (ES) vo Freqtrade — tie isté signály ako `TksStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksEsStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

__all__ = ["TksEsStrategy"]


class TksEsStrategy(TksStrategy):
    STRATEGY_KEY = "tkses"
    ENTRY_TAG_PREFIX = "tkses:"

    timeframe = "3m"
