"""TKS 1.0 MYM (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksMymNetStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

__all__ = ["TksMymNetStrategy"]


class TksMymNetStrategy(TksNetStrategy):
    STRATEGY_KEY = "tksmymnet"
    ENTRY_TAG_PREFIX = "tksmymnet:"

    timeframe = "3m"
