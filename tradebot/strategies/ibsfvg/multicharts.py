"""IBS FVG + IFVG v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSFvgSignal"]


class IBSFvgSignal(TradebotSignal):
    STRATEGY_KEY = "ibsfvg"
