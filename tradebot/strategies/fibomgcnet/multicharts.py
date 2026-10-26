"""Fibo 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FiboMgcNetSignal"]


class FiboMgcNetSignal(TradebotSignal):
    STRATEGY_KEY = "fibomgcnet"
