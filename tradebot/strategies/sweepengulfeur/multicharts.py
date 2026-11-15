"""SWEEPING ENGULF 1.0 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SweepEngulfEurSignal"]


class SweepEngulfEurSignal(TradebotSignal):
    STRATEGY_KEY = "sweepengulfeur"
