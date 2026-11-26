"""MTK EMAS 1.0 (MYM) vo Freqtrade — tie isté signály ako `MtkEmasStrategy`."""

from __future__ import annotations

from ..mtkemas.freqtrade import MtkEmasStrategy

__all__ = ["MtkEmasMymStrategy"]


class MtkEmasMymStrategy(MtkEmasStrategy):
    STRATEGY_KEY = "mtkemasmym"
    ENTRY_TAG_PREFIX = "mtkemasmym:"

    timeframe = "2h"
