"""VA NÁVRAT 1.0 (C# jadro) vo Freqtrade — tie isté signály ako `Va80Strategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/Va80NetStrategy.py`.
"""

from __future__ import annotations

from ..va80.freqtrade import Va80Strategy

__all__ = ["Va80NetStrategy"]


class Va80NetStrategy(Va80Strategy):
    STRATEGY_KEY = "va80net"
    ENTRY_TAG_PREFIX = "va80net:"

    timeframe = "1m"
