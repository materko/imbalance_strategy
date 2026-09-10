"""Gap Fill v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Gap_Signal.py`.
Stratégia nemá informatívny TF, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["GapSignal"]


class GapSignal(TradebotSignal):
    STRATEGY_KEY = "gap"
