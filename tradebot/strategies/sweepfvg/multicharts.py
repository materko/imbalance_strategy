"""SWEEP FVG 1.0 v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SweepFvgSignal"]


class SweepFvgSignal(TradebotSignal):
    STRATEGY_KEY = "sweepfvg"
