"""WILLIAMS %R LONG 1.0 (MYM) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["WprMymSignal"]


class WprMymSignal(TradebotSignal):
    STRATEGY_KEY = "wprmym"
