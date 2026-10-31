"""IVB 1.0 (ES) vo Freqtrade — tie isté signály ako `IvbStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IvbEsStrategy.py`.
"""

from __future__ import annotations

from ..ivb.freqtrade import IvbStrategy

__all__ = ["IvbEsStrategy"]


class IvbEsStrategy(IvbStrategy):
    STRATEGY_KEY = "ivbes"
    ENTRY_TAG_PREFIX = "ivbes:"

    timeframe = "5m"
