"""M2 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/M2_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["M2Signal"]


class M2Signal(TradebotSignal):
    STRATEGY_KEY = "m2"
