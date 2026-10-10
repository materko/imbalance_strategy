"""SWEEPING ENGULF 1.0 v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SweepEngulfSignal"]


class SweepEngulfSignal(TradebotSignal):
    STRATEGY_KEY = "sweepengulf"
