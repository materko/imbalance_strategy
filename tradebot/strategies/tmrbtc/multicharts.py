"""T-MEAN REVERSION 1.0 (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TmrBtcSignal"]


class TmrBtcSignal(TradebotSignal):
    STRATEGY_KEY = "tmrbtc"
