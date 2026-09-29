"""JSS v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Jss_Signal.py`.
TF štruktúry sa skladá z barov grafu, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["JssSignal"]


class JssSignal(TradebotSignal):
    STRATEGY_KEY = "jss"
