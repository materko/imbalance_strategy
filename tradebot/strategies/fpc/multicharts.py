"""FPC 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Fpc_Signal.py`. Na grafe stačí Data1 (1m).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["FpcSignal"]


class FpcSignal(TradebotSignal):
    STRATEGY_KEY = "fpc"
