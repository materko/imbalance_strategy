"""MTK EMAS 1.0 (ES) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkEmasEsSignal"]


class MtkEmasEsSignal(TradebotSignal):
    STRATEGY_KEY = "mtkemases"
