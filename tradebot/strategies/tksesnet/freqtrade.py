"""TKS 1.0 ES (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksEsNetStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

__all__ = ["TksEsNetStrategy"]


class TksEsNetStrategy(TksNetStrategy):
    STRATEGY_KEY = "tksesnet"
    ENTRY_TAG_PREFIX = "tksesnet:"

    timeframe = "3m"
