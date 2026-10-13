"""IBS Entry Zone (C# jadro) v MultiCharts — študia nad generickým `TradebotSignal` (C# jadro cez most).

Emulátor MultiCharts vo webapp s ňou beží ako s každou inou stratégiou. Živá študia v MultiCharts
potrebuje v jeho Pythone pythonnet alebo Mono; natívny domov tejto stratégie je NinjaTrader a MT5.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSEntryNetSignal"]


class IBSEntryNetSignal(TradebotSignal):
    STRATEGY_KEY = "ibsentrynet"
