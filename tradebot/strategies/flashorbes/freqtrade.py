"""FLASH TRIGGER ORB 1.0 (ES) vo Freqtrade — tie isté signály ako `FlashorbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FlashorbEsStrategy.py`.
"""

from __future__ import annotations

from ..flashorb.freqtrade import FlashorbStrategy

__all__ = ["FlashorbEsStrategy"]


class FlashorbEsStrategy(FlashorbStrategy):
    STRATEGY_KEY = "flashorbes"
    ENTRY_TAG_PREFIX = "flashorbes:"

    timeframe = "15m"
