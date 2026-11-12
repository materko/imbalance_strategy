"""LONDON LIQUIDITY IFVG 1.0 (MYM) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LliqMymSignal"]


class LliqMymSignal(TradebotSignal):
    STRATEGY_KEY = "lliqmym"
