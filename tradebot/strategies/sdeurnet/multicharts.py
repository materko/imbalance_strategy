"""SD ZÓNY EURUSD (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SdEurNetSignal"]


class SdEurNetSignal(TradebotSignal):
    STRATEGY_KEY = "sdeurnet"
