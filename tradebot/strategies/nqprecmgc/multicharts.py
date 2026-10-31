"""NQ PRECISION 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NqprecMgcSignal"]


class NqprecMgcSignal(TradebotSignal):
    STRATEGY_KEY = "nqprecmgc"
