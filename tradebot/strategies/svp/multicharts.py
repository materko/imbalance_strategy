"""Volume Profile POC v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Svp_Signal.py`.
Profil sa počíta z barov grafu, na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["SvpSignal"]


class SvpSignal(TradebotSignal):
    STRATEGY_KEY = "svp"
