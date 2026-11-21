"""IB RETRACE 1.0 MYM (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetMymNetStrategy.py`.
"""

from __future__ import annotations

from ..ibretnet.freqtrade import IbRetNetStrategy

__all__ = ["IbRetMymNetStrategy"]


class IbRetMymNetStrategy(IbRetNetStrategy):
    STRATEGY_KEY = "ibretmymnet"
    ENTRY_TAG_PREFIX = "ibretmymnet:"

    timeframe = "5m"
