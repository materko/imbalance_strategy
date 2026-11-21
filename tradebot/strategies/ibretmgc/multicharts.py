"""IB RETRACE 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IbRetMgcSignal"]


class IbRetMgcSignal(TradebotSignal):
    STRATEGY_KEY = "ibretmgc"
