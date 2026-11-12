"""IBS EZ MYM v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryMymSignal"]


class IBSEntryMymSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentrymym"
