"""NQ PRECISION 1.0 (ES) vo Freqtrade — tie isté signály ako `NqprecStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NqprecEsStrategy.py`.
"""

from __future__ import annotations

from ..nqprec.freqtrade import NqprecStrategy

__all__ = ["NqprecEsStrategy"]


class NqprecEsStrategy(NqprecStrategy):
    STRATEGY_KEY = "nqpreces"
    ENTRY_TAG_PREFIX = "nqpreces:"

    timeframe = "1m"
