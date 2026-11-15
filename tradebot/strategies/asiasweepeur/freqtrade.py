"""ASIA SWEEP 1.0 (6E) vo Freqtrade — tie isté signály ako `AsiaSweepStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/AsiaSweepEurStrategy.py`.
"""

from __future__ import annotations

from ..asiasweep.freqtrade import AsiaSweepStrategy

__all__ = ["AsiaSweepEurStrategy"]


class AsiaSweepEurStrategy(AsiaSweepStrategy):
    STRATEGY_KEY = "asiasweepeur"
    ENTRY_TAG_PREFIX = "asiasweepeur:"

    timeframe = "5m"
