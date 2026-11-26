"""MTK EMAS 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasMgcSignal"]


class MtkEmasMgcSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemasmgc"
