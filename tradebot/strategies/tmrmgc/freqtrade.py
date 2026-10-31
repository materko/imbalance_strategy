"""T-MEAN REVERSION 1.0 (MGC) vo Freqtrade — tie isté signály ako `TmrStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TmrMgcStrategy.py`.
"""

from __future__ import annotations

from ..tmr.freqtrade import TmrStrategy

__all__ = ["TmrMgcStrategy"]


class TmrMgcStrategy(TmrStrategy):
    STRATEGY_KEY = "tmrmgc"
    ENTRY_TAG_PREFIX = "tmrmgc:"

    timeframe = "15m"
