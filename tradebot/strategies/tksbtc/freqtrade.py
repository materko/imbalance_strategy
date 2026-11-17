"""TKS 1.0 (BTC) vo Freqtrade — tie isté signály ako `TksStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksBtcStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

__all__ = ["TksBtcStrategy"]


class TksBtcStrategy(TksStrategy):
    STRATEGY_KEY = "tksbtc"
    ENTRY_TAG_PREFIX = "tksbtc:"

    timeframe = "3m"
