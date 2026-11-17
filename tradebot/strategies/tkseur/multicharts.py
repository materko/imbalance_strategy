"""TKS 1.0 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TksEurSignal"]


class TksEurSignal(TradebotSignal):
    STRATEGY_KEY = "tkseur"
