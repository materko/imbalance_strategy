"""MTK EMAS v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasSignal"]


class MtkEmasSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemas"
