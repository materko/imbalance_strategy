"""Market Structure v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Structure_Signal.py`.
Stratégia nemá informatívny TF, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["StructureSignal"]


class StructureSignal(TradebotSignal):
    STRATEGY_KEY = "structure"
