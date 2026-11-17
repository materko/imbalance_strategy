"""TKS 1.0 BTC (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TksBtcNetSignal"]


class TksBtcNetSignal(TradebotSignal):
    STRATEGY_KEY = "tksbtcnet"
