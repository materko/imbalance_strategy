"""SIGMA BREAKOUT 1.0 (ES) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SigmaEsSignal"]


class SigmaEsSignal(TradebotSignal):
    STRATEGY_KEY = "sigmaes"
