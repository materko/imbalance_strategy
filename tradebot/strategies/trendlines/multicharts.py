"""Trendline Breakout v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Trendline_Signal.py`.
TF trendoviek sa skladá z barov grafu, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["TrendlineSignal"]


class TrendlineSignal(TradebotSignal):
    STRATEGY_KEY = "trendlines"
