"""SIGMA BREAKOUT 1.0 (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SigmaNetSignal"]


class SigmaNetSignal(TradebotSignal):
    STRATEGY_KEY = "sigmanet"
