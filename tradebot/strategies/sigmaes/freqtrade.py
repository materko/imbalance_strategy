"""SIGMA BREAKOUT 1.0 (ES) vo Freqtrade — tie isté signály ako `SigmaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaEsStrategy.py`.
"""

from __future__ import annotations

from ..sigma.freqtrade import SigmaStrategy

__all__ = ["SigmaEsStrategy"]


class SigmaEsStrategy(SigmaStrategy):
    STRATEGY_KEY = "sigmaes"
    ENTRY_TAG_PREFIX = "sigmaes:"

    timeframe = "5m"
