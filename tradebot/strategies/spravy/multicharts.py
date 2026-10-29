"""SPRÁVY v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Spravy_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SpravySignal"]


class SpravySignal(TradebotSignal):
    STRATEGY_KEY = "spravy"
