"""SD Zones v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/SDZone_Signal.py`.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SDZoneSignal"]


class SDZoneSignal(TradebotSignal):
    STRATEGY_KEY = "sdzone"
