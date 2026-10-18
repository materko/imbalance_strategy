"""NOA 1.0 (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most).

Emulátor MultiCharts vo webapp s ňou beží ako s každou inou stratégiou; natívny domov je NinjaTrader a MT5.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NoaNetSignal"]


class NoaNetSignal(TradebotSignal):
    STRATEGY_KEY = "noanet"
