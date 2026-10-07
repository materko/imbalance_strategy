"""ASIA SWEEP 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/AsiaSweep_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["AsiaSweepSignal"]


class AsiaSweepSignal(TradebotSignal):
    STRATEGY_KEY = "asiasweep"
