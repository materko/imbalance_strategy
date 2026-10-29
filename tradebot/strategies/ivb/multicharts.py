"""IVB v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Ivb_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IvbSignal"]


class IvbSignal(TradebotSignal):
    STRATEGY_KEY = "ivb"
