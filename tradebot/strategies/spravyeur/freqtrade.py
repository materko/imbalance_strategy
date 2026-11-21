"""SPRÁVY (EUR/USD) vo Freqtrade — tie isté signály ako `SpravyStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/SpravyEurStrategy.py`.
"""

from __future__ import annotations

from ..spravy.freqtrade import SpravyStrategy

__all__ = ["SpravyEurStrategy"]


class SpravyEurStrategy(SpravyStrategy):
    STRATEGY_KEY = "spravyeur"
    ENTRY_TAG_PREFIX = "spravyeur:"

    timeframe = "5m"
