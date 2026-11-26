"""MTK EMAS 1.0 (MGC) vo Freqtrade — tie isté signály ako `MtkEmasStrategy`."""

from __future__ import annotations

from ..mtkemas.freqtrade import MtkEmasStrategy

__all__ = ["MtkEmasMgcStrategy"]


class MtkEmasMgcStrategy(MtkEmasStrategy):
    STRATEGY_KEY = "mtkemasmgc"
    ENTRY_TAG_PREFIX = "mtkemasmgc:"

    timeframe = "4h"
