"""ORB 15/5 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Orb15MgcSignal"]


class Orb15MgcSignal(TradebotSignal):
    STRATEGY_KEY = "orb15mgc"
