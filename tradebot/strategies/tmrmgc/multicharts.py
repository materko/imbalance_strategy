"""T-MEAN REVERSION 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TmrMgcSignal"]


class TmrMgcSignal(TradebotSignal):
    STRATEGY_KEY = "tmrmgc"
