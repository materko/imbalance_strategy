"""IB RETRACE 1.0 MYM (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IbRetMymNetSignal"]


class IbRetMymNetSignal(TradebotSignal):
    STRATEGY_KEY = "ibretmymnet"
