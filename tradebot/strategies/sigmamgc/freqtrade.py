"""SIGMA BREAKOUT 1.0 (MGC) vo Freqtrade — tie isté signály ako `SigmaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaMgcStrategy.py`.
"""

from __future__ import annotations

from ..sigma.freqtrade import SigmaStrategy

__all__ = ["SigmaMgcStrategy"]


class SigmaMgcStrategy(SigmaStrategy):
    STRATEGY_KEY = "sigmamgc"
    ENTRY_TAG_PREFIX = "sigmamgc:"

    timeframe = "5m"
