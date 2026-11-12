"""NOA 1.0 MYM (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NoaMymNetSignal"]


class NoaMymNetSignal(TradebotSignal):
    STRATEGY_KEY = "noamymnet"
