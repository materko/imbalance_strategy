"""IBS v MultiCharts — študia nad generickým `TradebotSignal`.

Nič IBS-špecifické tu netreba: informatívny TF (Data2) a engine dodá registry.
Šablóna pre PowerLanguage .NET Editor je `platforms/multicharts/IBS_Signal.py`.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["IBSSignal"]


class IBSSignal(TradebotSignal):
    STRATEGY_KEY = "ibs"
