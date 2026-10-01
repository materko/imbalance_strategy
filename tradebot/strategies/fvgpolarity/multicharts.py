"""FVG POLARITY v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/FvgPolarity_Signal.py`. Na grafe stačí Data1 (15m).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FvgPolaritySignal"]


class FvgPolaritySignal(TradebotSignal):
    STRATEGY_KEY = "fvgpolarity"
