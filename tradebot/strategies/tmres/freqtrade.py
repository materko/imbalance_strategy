"""T-MEAN REVERSION 1.0 (ES) vo Freqtrade — tie isté signály ako `TmrStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TmrEsStrategy.py`.
"""

from __future__ import annotations

from ..tmr.freqtrade import TmrStrategy

__all__ = ["TmrEsStrategy"]


class TmrEsStrategy(TmrStrategy):
    STRATEGY_KEY = "tmres"
    ENTRY_TAG_PREFIX = "tmres:"

    timeframe = "15m"
