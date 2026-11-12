"""T-MEAN REVERSION 1.0 (MYM) vo Freqtrade — tie isté signály ako `TmrStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TmrMymStrategy.py`.
"""

from __future__ import annotations

from ..tmr.freqtrade import TmrStrategy

__all__ = ["TmrMymStrategy"]


class TmrMymStrategy(TmrStrategy):
    STRATEGY_KEY = "tmrmym"
    ENTRY_TAG_PREFIX = "tmrmym:"

    timeframe = "15m"
