"""M2 (MNQ) vo Freqtrade — tie isté signály ako `M2Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/M2MNQStrategy.py`.
"""

from __future__ import annotations

from ..m2.freqtrade import M2Strategy

__all__ = ["M2MNQStrategy"]


class M2MNQStrategy(M2Strategy):
    STRATEGY_KEY = "m2mnq"
    ENTRY_TAG_PREFIX = "m2mnq:"

    timeframe = "1m"
