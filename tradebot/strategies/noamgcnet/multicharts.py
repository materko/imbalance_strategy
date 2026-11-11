"""NOA 1.0 MGC (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NoaMgcNetSignal"]


class NoaMgcNetSignal(TradebotSignal):
    STRATEGY_KEY = "noamgcnet"
