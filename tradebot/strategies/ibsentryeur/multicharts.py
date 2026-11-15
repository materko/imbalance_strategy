"""IBS EZ 6E v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryEurSignal"]


class IBSEntryEurSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentryeur"
