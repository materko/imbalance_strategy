"""DAILY OPEN v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/DailyOpen_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["DailyOpenSignal"]


class DailyOpenSignal(TradebotSignal):
    STRATEGY_KEY = "dailyopen"
