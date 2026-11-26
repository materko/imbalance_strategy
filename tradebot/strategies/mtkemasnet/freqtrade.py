"""MTK EMAS 1.0 (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkEmasNetStrategy.py`.
"""

from __future__ import annotations

from ..mtkemas.freqtrade import MtkEmasStrategy

#: `enter_tag` obchodu je ``mtkemasnet:<…>``.
ENTRY_TAG_PREFIX = "mtkemasnet:"

__all__ = ["MtkEmasNetStrategy", "ENTRY_TAG_PREFIX"]


class MtkEmasNetStrategy(MtkEmasStrategy):
    """MTK EMAS 1.0 s jadrom v C# — tie isté signály ako `MtkEmasStrategy`, iný engine."""

    STRATEGY_KEY = "mtkemasnet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "4h"
