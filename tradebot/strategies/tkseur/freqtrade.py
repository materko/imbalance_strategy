"""TKS 1.0 (6E) vo Freqtrade — tie isté signály ako `TksStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksEurStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

__all__ = ["TksEurStrategy"]


class TksEurStrategy(TksStrategy):
    STRATEGY_KEY = "tkseur"
    ENTRY_TAG_PREFIX = "tkseur:"

    timeframe = "3m"
