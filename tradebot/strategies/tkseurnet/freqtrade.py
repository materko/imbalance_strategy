"""TKS 1.0 6E (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksEurNetStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

__all__ = ["TksEurNetStrategy"]


class TksEurNetStrategy(TksNetStrategy):
    STRATEGY_KEY = "tkseurnet"
    ENTRY_TAG_PREFIX = "tkseurnet:"

    timeframe = "3m"
