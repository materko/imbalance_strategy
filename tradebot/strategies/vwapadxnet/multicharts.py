"""VWAP ADX Pullback (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most).

Emulátor MultiCharts vo webapp s ňou beží ako s každou inou stratégiou; natívny domov je NinjaTrader a MT5.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VwapAdxNetSignal"]


class VwapAdxNetSignal(TradebotSignal):
    STRATEGY_KEY = "vwapadxnet"
