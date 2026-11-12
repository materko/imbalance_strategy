"""SIGMA BREAKOUT 1.0 MYM (C# jadro) vo Freqtrade — tie isté signály ako `SigmaMymStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaMymNetStrategy.py`.
"""

from __future__ import annotations

from ..sigmamym.freqtrade import SigmaMymStrategy

__all__ = ["SigmaMymNetStrategy"]


class SigmaMymNetStrategy(SigmaMymStrategy):
    STRATEGY_KEY = "sigmamymnet"
    ENTRY_TAG_PREFIX = "sigmamymnet:"

    timeframe = "5m"
