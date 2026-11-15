"""MTK ZONE (6E) v MultiCharts — študia nad generickým `TradebotSignal`."""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["MtkZoneEurSignal"]


class MtkZoneEurSignal(TradebotSignal):
    STRATEGY_KEY = "mtkzoneeur"
