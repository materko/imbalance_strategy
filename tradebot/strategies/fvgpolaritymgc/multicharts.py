"""FVG POLARITY (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FvgPolarityMgcSignal"]


class FvgPolarityMgcSignal(TradebotSignal):
    STRATEGY_KEY = "fvgpolaritymgc"
