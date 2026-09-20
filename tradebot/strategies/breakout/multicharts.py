"""Breakout v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Breakout_Signal.py`.
Stratégia má informatívny TF (otváracia sviečka), takže na grafe musí byť Data2 —
inak štúdia pri štarte povie, čo chýba.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["BreakoutSignal"]


class BreakoutSignal(TradebotSignal):
    STRATEGY_KEY = "breakout"
