"""IBS EZ ES v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryEsSignal"]


class IBSEntryEsSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentryes"
