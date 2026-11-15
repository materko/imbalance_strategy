"""ASIA SWEEP 1.0 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["AsiaSweepEurSignal"]


class AsiaSweepEurSignal(TradebotSignal):
    STRATEGY_KEY = "asiasweepeur"
