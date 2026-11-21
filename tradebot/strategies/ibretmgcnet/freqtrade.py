"""IB RETRACE 1.0 MGC (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetMgcNetStrategy.py`.
"""

from __future__ import annotations

from ..ibretnet.freqtrade import IbRetNetStrategy

__all__ = ["IbRetMgcNetStrategy"]


class IbRetMgcNetStrategy(IbRetNetStrategy):
    STRATEGY_KEY = "ibretmgcnet"
    ENTRY_TAG_PREFIX = "ibretmgcnet:"

    timeframe = "5m"
