"""M2 (MGC) vo Freqtrade — tie isté signály ako `M2Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/M2MGCStrategy.py`.
"""

from __future__ import annotations

from ..m2.freqtrade import M2Strategy

__all__ = ["M2MGCStrategy"]


class M2MGCStrategy(M2Strategy):
    STRATEGY_KEY = "m2mgc"
    ENTRY_TAG_PREFIX = "m2mgc:"

    timeframe = "1m"
