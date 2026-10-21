"""FVG POLARITY (MGC) vo Freqtrade — tie isté signály ako `FvgPolarityStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/FvgPolarityMgcStrategy.py`.
"""

from __future__ import annotations

from ..fvgpolarity.freqtrade import FvgPolarityStrategy

__all__ = ["FvgPolarityMgcStrategy"]


class FvgPolarityMgcStrategy(FvgPolarityStrategy):
    STRATEGY_KEY = "fvgpolaritymgc"
    ENTRY_TAG_PREFIX = "fvgpolaritymgc:"

    timeframe = "3m"
