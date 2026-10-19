"""VWAP ORB 1.5 (C# jadro EOD) vo Freqtrade — adaptér nad C# jadrom, tie isté signály ako `VwapOrbNetStrategy` + koniec dňa 15:59 NY.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/VwapOrbNetEodStrategy.py`.
"""

from __future__ import annotations

from ..vwaporbnet.freqtrade import VwapOrbNetStrategy

#: `enter_tag` obchodu je ``vwaporbneteod:<…>``.
ENTRY_TAG_PREFIX = "vwaporbneteod:"

__all__ = ["VwapOrbNetEodStrategy", "ENTRY_TAG_PREFIX"]


class VwapOrbNetEodStrategy(VwapOrbNetStrategy):
    """VWAP ORB 1.5 (C# jadro EOD) — signály predlohy, o 15:59 New York všetko zavreté."""

    STRATEGY_KEY = "vwaporbneteod"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "5m"
