"""NQ PRECISION 1.0 (ES) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NqprecEsSignal"]


class NqprecEsSignal(TradebotSignal):
    STRATEGY_KEY = "nqpreces"
