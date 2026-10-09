"""VWAP ADX v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/VwapAdx_Signal.py`. Na grafe stačí Data1 (1m) so skutočným objemom.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VwapAdxSignal"]


class VwapAdxSignal(TradebotSignal):
    STRATEGY_KEY = "vwapadx"
