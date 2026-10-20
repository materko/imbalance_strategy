"""TKS 1.0 (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksNetStrategy.py`.
"""

from __future__ import annotations

from ..tks.freqtrade import TksStrategy

#: `enter_tag` obchodu je ``tksnet:<…>``.
ENTRY_TAG_PREFIX = "tksnet:"

__all__ = ["TksNetStrategy", "ENTRY_TAG_PREFIX"]


class TksNetStrategy(TksStrategy):
    """TKS 1.0 s jadrom v C# — tie isté signály ako `TksStrategy`, iný engine."""

    STRATEGY_KEY = "tksnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
