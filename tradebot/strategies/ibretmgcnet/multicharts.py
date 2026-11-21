"""IB RETRACE 1.0 MGC (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IbRetMgcNetSignal"]


class IbRetMgcNetSignal(TradebotSignal):
    STRATEGY_KEY = "ibretmgcnet"
