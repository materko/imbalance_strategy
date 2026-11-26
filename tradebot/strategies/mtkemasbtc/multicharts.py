"""MTK EMAS 1.0 (BTC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasBtcSignal"]


class MtkEmasBtcSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemasbtc"
