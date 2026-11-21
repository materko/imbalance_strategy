"""SPRÁVY EUR/USD (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SpravyEurNetSignal"]


class SpravyEurNetSignal(TradebotSignal):
    STRATEGY_KEY = "spravyeurnet"
