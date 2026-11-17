"""TKS 1.0 MYM (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TksMymNetSignal"]


class TksMymNetSignal(TradebotSignal):
    STRATEGY_KEY = "tksmymnet"
