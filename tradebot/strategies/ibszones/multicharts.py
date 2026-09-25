"""IBSZones v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSZonesSignal"]


class IBSZonesSignal(TradebotSignal):
    STRATEGY_KEY = "ibszones"
