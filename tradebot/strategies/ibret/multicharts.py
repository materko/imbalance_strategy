"""IB RETRACE 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/IbRet_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IbRetSignal"]


class IbRetSignal(TradebotSignal):
    STRATEGY_KEY = "ibret"
