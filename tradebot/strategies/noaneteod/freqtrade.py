"""NOA 1.0 (C# jadro EOD) vo Freqtrade — adaptér nad C# jadrom, tie isté signály ako `NoaNetStrategy` + koniec dňa 15:59 NY.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/NoaNetEodStrategy.py`.
"""

from __future__ import annotations

from ..noanet.freqtrade import NoaNetStrategy

#: `enter_tag` obchodu je ``noaneteod:<…>``.
ENTRY_TAG_PREFIX = "noaneteod:"

__all__ = ["NoaNetEodStrategy", "ENTRY_TAG_PREFIX"]


class NoaNetEodStrategy(NoaNetStrategy):
    """NOA 1.0 (C# jadro EOD) — signály predlohy, o 15:59 New York všetko zavreté."""

    STRATEGY_KEY = "noaneteod"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "5m"
