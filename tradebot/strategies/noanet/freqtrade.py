"""NOA 1.0 (C# jadro) vo Freqtrade — adaptér nad C# jadrom. 

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaNetStrategy.py`.
"""

from __future__ import annotations

from ..noa.freqtrade import NoaStrategy

#: `enter_tag` obchodu je ``noanet:<…>``.
ENTRY_TAG_PREFIX = "noanet:"

__all__ = ["NoaNetStrategy", "ENTRY_TAG_PREFIX"]


class NoaNetStrategy(NoaStrategy):
    """NOA 1.0 s jadrom v C# — tie isté signály ako `NoaStrategy`, iný engine."""

    STRATEGY_KEY = "noanet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "5m"
