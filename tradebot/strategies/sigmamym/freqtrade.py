"""SIGMA BREAKOUT 1.0 (MYM) vo Freqtrade — tie isté signály ako `SigmaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaMymStrategy.py`.
"""

from __future__ import annotations

from ..sigma.freqtrade import SigmaStrategy

__all__ = ["SigmaMymStrategy"]


class SigmaMymStrategy(SigmaStrategy):
    STRATEGY_KEY = "sigmamym"
    ENTRY_TAG_PREFIX = "sigmamym:"

    timeframe = "5m"
