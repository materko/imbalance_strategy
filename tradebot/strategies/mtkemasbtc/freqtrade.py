"""MTK EMAS 1.0 (BTC) vo Freqtrade — tie isté signály ako `MtkEmasStrategy`."""

from __future__ import annotations

from ..mtkemas.freqtrade import MtkEmasStrategy

__all__ = ["MtkEmasBtcStrategy"]


class MtkEmasBtcStrategy(MtkEmasStrategy):
    STRATEGY_KEY = "mtkemasbtc"
    ENTRY_TAG_PREFIX = "mtkemasbtc:"

    timeframe = "4h"
