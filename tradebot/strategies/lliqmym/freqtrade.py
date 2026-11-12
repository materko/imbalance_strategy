"""LONDON LIQUIDITY IFVG 1.0 (MYM) vo Freqtrade — tie isté signály ako `LliqStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/LliqMymStrategy.py`.
"""

from __future__ import annotations

from ..lliq.freqtrade import LliqStrategy

__all__ = ["LliqMymStrategy"]


class LliqMymStrategy(LliqStrategy):
    STRATEGY_KEY = "lliqmym"
    ENTRY_TAG_PREFIX = "lliqmym:"

    timeframe = "5m"
