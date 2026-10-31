"""FLASH TRIGGER ORB 1.0 (MGC) vo Freqtrade — tie isté signály ako `FlashorbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FlashorbMgcStrategy.py`.
"""

from __future__ import annotations

from ..flashorb.freqtrade import FlashorbStrategy

__all__ = ["FlashorbMgcStrategy"]


class FlashorbMgcStrategy(FlashorbStrategy):
    STRATEGY_KEY = "flashorbmgc"
    ENTRY_TAG_PREFIX = "flashorbmgc:"

    timeframe = "15m"
