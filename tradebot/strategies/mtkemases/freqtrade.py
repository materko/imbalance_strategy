"""MTK EMAS 1.0 (ES) vo Freqtrade — tie isté signály ako `MtkEmasStrategy`."""

from __future__ import annotations

from ..mtkemas.freqtrade import MtkEmasStrategy

__all__ = ["MtkEmasEsStrategy"]


class MtkEmasEsStrategy(MtkEmasStrategy):
    STRATEGY_KEY = "mtkemases"
    ENTRY_TAG_PREFIX = "mtkemases:"

    timeframe = "1h"
