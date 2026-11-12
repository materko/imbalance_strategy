"""WILLIAMS %R LONG 1.0 MYM (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["WprMymNetSignal"]


class WprMymNetSignal(TradebotSignal):
    STRATEGY_KEY = "wprmymnet"
