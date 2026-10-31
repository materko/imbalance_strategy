"""LONDON LIQUIDITY IFVG 1.0 (ES) vo Freqtrade — tie isté signály ako `LliqStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/LliqEsStrategy.py`.
"""

from __future__ import annotations

from ..lliq.freqtrade import LliqStrategy

__all__ = ["LliqEsStrategy"]


class LliqEsStrategy(LliqStrategy):
    STRATEGY_KEY = "lliqes"
    ENTRY_TAG_PREFIX = "lliqes:"

    timeframe = "5m"
