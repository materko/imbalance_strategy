"""M2 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["M2MGCSignal"]


class M2MGCSignal(TradebotSignal):
    STRATEGY_KEY = "m2mgc"
