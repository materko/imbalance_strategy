"""MTK ZONE v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkZoneSignal"]


class MtkZoneSignal(TradebotSignal):
    STRATEGY_KEY = "mtkzone"
