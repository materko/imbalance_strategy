"""FLASH TRIGGER ORB 1.0 (BTC) vo Freqtrade — tie isté signály ako `FlashorbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FlashorbBtcStrategy.py`.
"""

from __future__ import annotations

from ..flashorb.freqtrade import FlashorbStrategy

__all__ = ["FlashorbBtcStrategy"]


class FlashorbBtcStrategy(FlashorbStrategy):
    STRATEGY_KEY = "flashorbbtc"
    ENTRY_TAG_PREFIX = "flashorbbtc:"

    timeframe = "15m"
