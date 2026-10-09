"""Volt Break v MultiCharts — študia nad generickým `TradebotSignal` (Data1 30m)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VoltBreakSignal"]


class VoltBreakSignal(TradebotSignal):
    STRATEGY_KEY = "voltbreak"
