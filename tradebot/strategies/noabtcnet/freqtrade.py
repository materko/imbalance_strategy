"""NOA 1.0 BTC (C# jadro) vo Freqtrade.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaBtcNetStrategy.py`.
"""

from __future__ import annotations

from ..noabtc.freqtrade import NoaBtcStrategy

__all__ = ["NoaBtcNetStrategy"]


class NoaBtcNetStrategy(NoaBtcStrategy):
    STRATEGY_KEY = "noabtcnet"
    ENTRY_TAG_PREFIX = "noabtcnet:"

    timeframe = "5m"
