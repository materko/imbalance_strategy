"""IBS FVG + IFVG vo Freqtrade — vyššie TF si vrstva FVG skladá z barov grafu sama."""

from __future__ import annotations

from ..ibs.freqtrade import IBSImbalanceStrategy

#: `enter_tag` obchodu je ``ibsfvg:<čas baru signálu v ms>``.
ENTRY_TAG_PREFIX = "ibsfvg:"

__all__ = ["IBSFvgStrategy", "ENTRY_TAG_PREFIX"]


class IBSFvgStrategy(IBSImbalanceStrategy):
    """IBS entry model len nad zónami z FVG a IFVG."""

    STRATEGY_KEY = "ibsfvg"
    ENTRY_TAG_PREFIX = ENTRY_TAG_PREFIX

    timeframe = "3m"
