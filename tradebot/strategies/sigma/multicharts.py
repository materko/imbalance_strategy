"""SIGMA BREAKOUT 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Sigma_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SigmaSignal"]


class SigmaSignal(TradebotSignal):
    STRATEGY_KEY = "sigma"
