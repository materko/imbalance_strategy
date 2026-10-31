"""FLASH TRIGGER ORB 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Flashorb_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FlashorbSignal"]


class FlashorbSignal(TradebotSignal):
    STRATEGY_KEY = "flashorb"
