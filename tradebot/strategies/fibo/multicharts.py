"""Fibo v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Fibo_Signal.py`.
TF swingov sa skladá z barov grafu, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FiboSignal"]


class FiboSignal(TradebotSignal):
    STRATEGY_KEY = "fibo"
