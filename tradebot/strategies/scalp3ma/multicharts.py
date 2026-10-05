"""Scalping 3MA + RSI + fraktál v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Scalp3Ma_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Scalp3MaSignal"]


class Scalp3MaSignal(TradebotSignal):
    STRATEGY_KEY = "scalp3ma"
