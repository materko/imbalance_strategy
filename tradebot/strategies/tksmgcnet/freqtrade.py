"""TKS 1.0 MGC (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksMgcNetStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

__all__ = ["TksMgcNetStrategy"]


class TksMgcNetStrategy(TksNetStrategy):
    STRATEGY_KEY = "tksmgcnet"
    ENTRY_TAG_PREFIX = "tksmgcnet:"

    timeframe = "3m"
