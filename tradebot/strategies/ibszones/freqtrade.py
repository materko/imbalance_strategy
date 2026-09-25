"""IBSZones vo Freqtrade — IBS s okným detekčného TF zo `ZoneSyncHTFFeeder`.

Všetko ostatné (koniec seansy, timeout limitky, sizing) sa dedí z IBS; feeder si berie
generický runner zo `StrategySpec.htf_feeder`, takže tu nie je čo prepisovať.
"""

from __future__ import annotations

from ..ibs.freqtrade import IBSImbalanceStrategy

#: `enter_tag` obchodu je ``ibszones:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibszones:"

__all__ = ["IBSZonesStrategy", "ENTRY_TAG_PREFIX"]


class IBSZonesStrategy(IBSImbalanceStrategy):
    """IBS so zónami, ktoré nezávisia od TF grafu."""

    STRATEGY_KEY = "ibszones"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
