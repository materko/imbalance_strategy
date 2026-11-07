"""VA NÁVRAT 1.0 (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Va80NetSignal"]


class Va80NetSignal(TradebotSignal):
    STRATEGY_KEY = "va80net"
