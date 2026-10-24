"""NY VA SHAPE v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NyVaShapeSignal"]


class NyVaShapeSignal(TradebotSignal):
    STRATEGY_KEY = "nyvashape"
