"""VALUE AREA REVERSION 1.0 v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VaRevSignal"]


class VaRevSignal(TradebotSignal):
    STRATEGY_KEY = "varev"
