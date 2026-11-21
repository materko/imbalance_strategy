"""SPRÁVY (EUR/USD) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SpravyEurSignal"]


class SpravyEurSignal(TradebotSignal):
    STRATEGY_KEY = "spravyeur"
