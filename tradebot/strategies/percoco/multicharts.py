"""Craig Percoco 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Percoco_Signal.py`.
15m sa skladá z barov grafu, na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["PercocoSignal"]


class PercocoSignal(TradebotSignal):
    STRATEGY_KEY = "percoco"
