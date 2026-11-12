"""NOA 1.0 (MYM) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NoaMymSignal"]


class NoaMymSignal(TradebotSignal):
    STRATEGY_KEY = "noamym"
