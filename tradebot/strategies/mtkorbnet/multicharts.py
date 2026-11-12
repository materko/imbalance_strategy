"""MTK ORB MGC (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkOrbNetSignal"]


class MtkOrbNetSignal(TradebotSignal):
    STRATEGY_KEY = "mtkorbnet"
