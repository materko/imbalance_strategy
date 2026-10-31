"""WILLIAMS %R LONG 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Wpr_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["WprSignal"]


class WprSignal(TradebotSignal):
    STRATEGY_KEY = "wpr"
