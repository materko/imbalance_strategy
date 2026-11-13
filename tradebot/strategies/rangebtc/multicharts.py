"""Range Breakout (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["RangeBtcSignal"]


class RangeBtcSignal(TradebotSignal):
    STRATEGY_KEY = "rangebtc"
