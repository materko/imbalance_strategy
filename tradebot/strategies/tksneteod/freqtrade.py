"""TKS 1.0 (C# jadro EOD) vo Freqtrade — adaptér nad C# jadrom, tie isté signály ako `TksNetStrategy` + koniec dňa 15:59 NY.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/TksNetEodStrategy.py`.
"""

from __future__ import annotations

from ..tksnet.freqtrade import TksNetStrategy

#: `enter_tag` obchodu je ``tksneteod:<…>``.
ENTRY_TAG_PREFIX = "tksneteod:"

__all__ = ["TksNetEodStrategy", "ENTRY_TAG_PREFIX"]


class TksNetEodStrategy(TksNetStrategy):
    """TKS 1.0 (C# jadro EOD) — signály predlohy, o 15:59 New York všetko zavreté."""

    STRATEGY_KEY = "tksneteod"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
