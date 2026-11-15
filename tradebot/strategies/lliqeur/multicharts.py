"""LONDON LIQUIDITY IFVG 1.0 (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LliqEurSignal"]


class LliqEurSignal(TradebotSignal):
    STRATEGY_KEY = "lliqeur"
