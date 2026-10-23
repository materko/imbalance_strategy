"""NY VA BREAKOUT ES v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NyVaEsSignal"]


class NyVaEsSignal(TradebotSignal):
    STRATEGY_KEY = "nyvaes"
