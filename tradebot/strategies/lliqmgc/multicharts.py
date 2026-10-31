"""LONDON LIQUIDITY IFVG 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LliqMgcSignal"]


class LliqMgcSignal(TradebotSignal):
    STRATEGY_KEY = "lliqmgc"
