"""IBS EZ MYM (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most)."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryMymNetSignal"]


class IBSEntryMymNetSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentrymymnet"
