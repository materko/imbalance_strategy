"""M2 (MNQ) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["M2MNQSignal"]


class M2MNQSignal(TradebotSignal):
    STRATEGY_KEY = "m2mnq"
