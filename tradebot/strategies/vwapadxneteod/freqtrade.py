"""VWAP ADX Pullback (C# jadro EOD) vo Freqtrade — adaptér nad C# jadrom, tie isté signály ako `VwapAdxNetStrategy` + koniec dňa 15:59 NY.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapAdxNetEodStrategy.py`.
"""

from __future__ import annotations

from ..vwapadxnet.freqtrade import VwapAdxNetStrategy

#: `enter_tag` obchodu je ``vwapadxneteod:<…>``.
ENTRY_TAG_PREFIX = "vwapadxneteod:"

__all__ = ["VwapAdxNetEodStrategy", "ENTRY_TAG_PREFIX"]


class VwapAdxNetEodStrategy(VwapAdxNetStrategy):
    """VWAP ADX Pullback (C# jadro EOD) — signály predlohy, o 15:59 New York všetko zavreté."""

    STRATEGY_KEY = "vwapadxneteod"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "1m"
