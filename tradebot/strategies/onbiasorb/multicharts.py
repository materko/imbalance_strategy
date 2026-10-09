"""Overnight Bias ORB v MultiCharts — študia nad generickým `TradebotSignal` (Data1 15m)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["OnBiasOrbSignal"]


class OnBiasOrbSignal(TradebotSignal):
    STRATEGY_KEY = "onbiasorb"
