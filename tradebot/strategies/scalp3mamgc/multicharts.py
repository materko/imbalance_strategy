"""Scalping 3MA (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Scalp3MaMgcSignal"]


class Scalp3MaMgcSignal(TradebotSignal):
    STRATEGY_KEY = "scalp3mamgc"
