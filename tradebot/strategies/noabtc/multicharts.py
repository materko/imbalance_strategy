"""NOA 1.0 (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NoaBtcSignal"]


class NoaBtcSignal(TradebotSignal):
    STRATEGY_KEY = "noabtc"
