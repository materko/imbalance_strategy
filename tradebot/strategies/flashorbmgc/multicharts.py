"""FLASH TRIGGER ORB 1.0 (MGC) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FlashorbMgcSignal"]


class FlashorbMgcSignal(TradebotSignal):
    STRATEGY_KEY = "flashorbmgc"
