"""TKS 1.0 6E (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TksEurNetSignal"]


class TksEurNetSignal(TradebotSignal):
    STRATEGY_KEY = "tkseurnet"
