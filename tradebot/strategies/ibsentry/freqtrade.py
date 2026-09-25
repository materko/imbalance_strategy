"""IBS Entry Zone vo Freqtrade.

Vyššie TF (5m/15m/30m/1h) si vrstva skladá z barov grafu sama, takže tu nepribúda
žiadny informatívny pár nad rámec toho, čo potrebuje IBS.
"""

from __future__ import annotations

from ..ibs.freqtrade import IBSImbalanceStrategy

#: `enter_tag` obchodu je ``ibsentry:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsentry:"

__all__ = ["IBSEntryZoneStrategy", "ENTRY_TAG_PREFIX"]


class IBSEntryZoneStrategy(IBSImbalanceStrategy):
    """IBS, ktorému vstupy povoľujú alebo zakazujú veľké imbalance zóny."""

    STRATEGY_KEY = "ibsentry"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
