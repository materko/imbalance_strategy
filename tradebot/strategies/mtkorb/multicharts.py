"""MTK ORB (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkOrbSignal"]


class MtkOrbSignal(TradebotSignal):
    STRATEGY_KEY = "mtkorb"
