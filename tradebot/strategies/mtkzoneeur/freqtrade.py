"""MTK ZONE (6E) vo Freqtrade — tie isté signály ako `MtkZoneStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkZoneEurStrategy.py`.
"""

from __future__ import annotations

from ..mtkzone.freqtrade import MtkZoneStrategy

__all__ = ["MtkZoneEurStrategy"]


class MtkZoneEurStrategy(MtkZoneStrategy):
    STRATEGY_KEY = "mtkzoneeur"
    ENTRY_TAG_PREFIX = "mtkzoneeur:"

    timeframe = "3m"
