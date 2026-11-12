"""MTK ORB MGC (C# jadro) vo Freqtrade — tie isté signály ako `MtkOrbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkOrbNetStrategy.py`.
"""

from __future__ import annotations

from ..mtkorb.freqtrade import MtkOrbStrategy

__all__ = ["MtkOrbNetStrategy"]


class MtkOrbNetStrategy(MtkOrbStrategy):
    STRATEGY_KEY = "mtkorbnet"
    ENTRY_TAG_PREFIX = "mtkorbnet:"

    timeframe = "5m"
