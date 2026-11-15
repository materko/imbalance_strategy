"""LONDON LIQUIDITY IFVG 1.0 (6E) vo Freqtrade — tie isté signály ako `LliqStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/LliqEurStrategy.py`.
"""

from __future__ import annotations

from ..lliq.freqtrade import LliqStrategy

__all__ = ["LliqEurStrategy"]


class LliqEurStrategy(LliqStrategy):
    STRATEGY_KEY = "lliqeur"
    ENTRY_TAG_PREFIX = "lliqeur:"

    timeframe = "5m"
