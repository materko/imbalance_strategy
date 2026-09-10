"""ORB v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/ORB_Signal.py`.
Stratégia nemá informatívny TF, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["ORBSignal"]


class ORBSignal(TradebotSignal):
    STRATEGY_KEY = "orb"
