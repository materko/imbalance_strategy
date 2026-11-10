"""MTK ZONE (C# jadro) vo Freqtrade — adaptér nad C# jadrom.

Shim pre resolver: `deploy/freqtrade/user_data/strategies/MtkZoneNetStrategy.py`.
"""

from __future__ import annotations

from ..mtkzone.freqtrade import MtkZoneStrategy

#: `enter_tag` obchodu je ``mtkzonenet:<…>``.
ENTRY_TAG_PREFIX = "mtkzonenet:"

__all__ = ["MtkZoneNetStrategy", "ENTRY_TAG_PREFIX"]


class MtkZoneNetStrategy(MtkZoneStrategy):
    """MTK ZONE s jadrom v C# — tie isté signály ako `MtkZoneStrategy`, iný engine."""

    STRATEGY_KEY = "mtkzonenet"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
