"""SIGMA BREAKOUT 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SigmaMgcSignal"]


class SigmaMgcSignal(TradebotSignal):
    STRATEGY_KEY = "sigmamgc"
