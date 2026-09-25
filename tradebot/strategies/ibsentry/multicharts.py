"""IBS Entry Zone v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryZoneSignal"]


class IBSEntryZoneSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentry"
