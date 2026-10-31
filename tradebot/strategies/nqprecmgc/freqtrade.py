"""NQ PRECISION 1.0 (MGC) vo Freqtrade — tie isté signály ako `NqprecStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NqprecMgcStrategy.py`.
"""

from __future__ import annotations

from ..nqprec.freqtrade import NqprecStrategy

__all__ = ["NqprecMgcStrategy"]


class NqprecMgcStrategy(NqprecStrategy):
    STRATEGY_KEY = "nqprecmgc"
    ENTRY_TAG_PREFIX = "nqprecmgc:"

    timeframe = "1m"
