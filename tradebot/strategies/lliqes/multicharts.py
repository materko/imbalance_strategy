"""LONDON LIQUIDITY IFVG 1.0 (ES) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LliqEsSignal"]


class LliqEsSignal(TradebotSignal):
    STRATEGY_KEY = "lliqes"
