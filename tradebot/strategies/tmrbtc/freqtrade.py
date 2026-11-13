"""T-MEAN REVERSION 1.0 (BTC) vo Freqtrade — tie isté signály ako `TmrStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TmrBtcStrategy.py`.
"""

from __future__ import annotations

from ..tmr.freqtrade import TmrStrategy

__all__ = ["TmrBtcStrategy"]


class TmrBtcStrategy(TmrStrategy):
    STRATEGY_KEY = "tmrbtc"
    ENTRY_TAG_PREFIX = "tmrbtc:"

    timeframe = "15m"
