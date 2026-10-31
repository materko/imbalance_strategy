"""LONDON LIQUIDITY IFVG 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Lliq_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LliqSignal"]


class LliqSignal(TradebotSignal):
    STRATEGY_KEY = "lliq"
