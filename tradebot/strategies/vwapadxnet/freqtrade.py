"""VWAP ADX Pullback (C# jadro) vo Freqtrade — adaptér nad C# jadrom. Len long.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapAdxNetStrategy.py`.
"""

from __future__ import annotations

from ..vwapadx.freqtrade import VwapAdxStrategy

#: `enter_tag` obchodu je ``vwapadxnet:<…>``.
ENTRY_TAG_PREFIX = "vwapadxnet:"

__all__ = ["VwapAdxNetStrategy", "ENTRY_TAG_PREFIX"]


class VwapAdxNetStrategy(VwapAdxStrategy):
    """VWAP ADX Pullback s jadrom v C# — tie isté signály ako `VwapAdxStrategy`, iný engine."""

    STRATEGY_KEY = "vwapadxnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "1m"
