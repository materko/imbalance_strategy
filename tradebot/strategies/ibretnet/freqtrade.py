"""IB RETRACE 1.0 (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/IbRetNetStrategy.py`.
"""

from __future__ import annotations

from ..ibret.freqtrade import IbRetStrategy

#: `enter_tag` obchodu je ``ibretnet:<…>``.
ENTRY_TAG_PREFIX = "ibretnet:"

__all__ = ["IbRetNetStrategy", "ENTRY_TAG_PREFIX"]


class IbRetNetStrategy(IbRetStrategy):
    """IB RETRACE 1.0 s jadrom v C# — tie isté signály ako `IbRetStrategy`, iný engine."""

    STRATEGY_KEY = "ibretnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "5m"
