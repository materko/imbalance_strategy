"""Fibo 1.0 MGC (C# jadro) vo Freqtrade — tie isté signály ako `FiboStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FiboMgcStrategy.py`.
"""

from __future__ import annotations

from ..fibomgc.freqtrade import FiboMgcStrategy

__all__ = ["FiboMgcNetStrategy"]


class FiboMgcNetStrategy(FiboMgcStrategy):
    STRATEGY_KEY = "fibomgcnet"
    ENTRY_TAG_PREFIX = "fibomgcnet:"

    timeframe = "3m"
