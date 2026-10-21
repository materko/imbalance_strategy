"""Scalping 3MA (MGC) vo Freqtrade — tie isté signály ako `Scalp3MaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Scalp3MaMgcStrategy.py`.
"""

from __future__ import annotations

from ..scalp3ma.freqtrade import Scalp3MaStrategy

__all__ = ["Scalp3MaMgcStrategy"]


class Scalp3MaMgcStrategy(Scalp3MaStrategy):
    STRATEGY_KEY = "scalp3mamgc"
    ENTRY_TAG_PREFIX = "scalp3mamgc:"

    timeframe = "15m"
