"""LONDON LIQUIDITY IFVG 1.0 (MGC) vo Freqtrade — tie isté signály ako `LliqStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/LliqMgcStrategy.py`.
"""

from __future__ import annotations

from ..lliq.freqtrade import LliqStrategy

__all__ = ["LliqMgcStrategy"]


class LliqMgcStrategy(LliqStrategy):
    STRATEGY_KEY = "lliqmgc"
    ENTRY_TAG_PREFIX = "lliqmgc:"

    timeframe = "5m"
