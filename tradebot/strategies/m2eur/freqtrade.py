"""M2 (6E) vo Freqtrade — tie isté signály ako `M2Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/M2EURStrategy.py`.
"""

from __future__ import annotations

from ..m2.freqtrade import M2Strategy

__all__ = ["M2EURStrategy"]


class M2EURStrategy(M2Strategy):
    STRATEGY_KEY = "m2eur"
    ENTRY_TAG_PREFIX = "m2eur:"

    timeframe = "1m"
