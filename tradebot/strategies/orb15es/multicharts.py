"""ORB 15/5 1.0 (ES) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Orb15EsSignal"]


class Orb15EsSignal(TradebotSignal):
    STRATEGY_KEY = "orb15es"
