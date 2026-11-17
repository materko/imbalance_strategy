"""TKS 1.0 BTC (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksBtcNetStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

__all__ = ["TksBtcNetStrategy"]


class TksBtcNetStrategy(TksNetStrategy):
    STRATEGY_KEY = "tksbtcnet"
    ENTRY_TAG_PREFIX = "tksbtcnet:"

    timeframe = "3m"
