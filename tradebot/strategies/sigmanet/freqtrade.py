"""SIGMA BREAKOUT 1.0 (C# jadro) vo Freqtrade — tie isté signály ako `SigmaStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaNetStrategy.py`.
"""

from __future__ import annotations

from ..sigma.freqtrade import SigmaStrategy

__all__ = ["SigmaNetStrategy"]


class SigmaNetStrategy(SigmaStrategy):
    STRATEGY_KEY = "sigmanet"
    ENTRY_TAG_PREFIX = "sigmanet:"

    timeframe = "5m"
