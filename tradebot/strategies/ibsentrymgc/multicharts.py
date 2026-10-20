"""IBS EZ MGC v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryMgcSignal"]


class IBSEntryMgcSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentrymgc"
