"""SIGMA BREAKOUT 1.0 MGC (C# jadro) vo Freqtrade — tie isté signály ako `SigmaMgcStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SigmaMgcNetStrategy.py`.
"""

from __future__ import annotations

from ..sigmamgc.freqtrade import SigmaMgcStrategy

__all__ = ["SigmaMgcNetStrategy"]


class SigmaMgcNetStrategy(SigmaMgcStrategy):
    STRATEGY_KEY = "sigmamgcnet"
    ENTRY_TAG_PREFIX = "sigmamgcnet:"

    timeframe = "5m"
