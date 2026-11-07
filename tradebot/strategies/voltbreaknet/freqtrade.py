"""Volt Break (C# jadro) vo Freqtrade — tie isté signály ako `VoltBreakStrategy`.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VoltBreakNetStrategy.py`.
"""

from __future__ import annotations

from ..voltbreak.freqtrade import VoltBreakStrategy

__all__ = ["VoltBreakNetStrategy"]


class VoltBreakNetStrategy(VoltBreakStrategy):
    STRATEGY_KEY = "voltbreaknet"
    ENTRY_TAG_PREFIX = "voltbreaknet:"

    timeframe = "30m"
