"""Overnight Bias ORB (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["OnBiasOrbBtcSignal"]


class OnBiasOrbBtcSignal(TradebotSignal):
    STRATEGY_KEY = "onbiasorbbtc"
