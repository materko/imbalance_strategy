"""M2 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["M2EURSignal"]


class M2EURSignal(TradebotSignal):
    STRATEGY_KEY = "m2eur"
