"""Fibo 1.0 (MGC) vo Freqtrade — tie isté signály ako `FiboStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FiboMgcStrategy.py`.
"""

from __future__ import annotations

from ..fibo.freqtrade import FiboStrategy

__all__ = ["FiboMgcStrategy"]


class FiboMgcStrategy(FiboStrategy):
    STRATEGY_KEY = "fibomgc"
    ENTRY_TAG_PREFIX = "fibomgc:"

    timeframe = "3m"
