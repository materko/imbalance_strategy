"""ORB 15/5 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Orb15_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Orb15Signal"]


class Orb15Signal(TradebotSignal):
    STRATEGY_KEY = "orb15"
