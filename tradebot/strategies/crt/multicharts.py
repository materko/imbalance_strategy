"""CRT + TBS v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Crt_Signal.py`.
TF rangu sa skladá z barov grafu, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["CrtSignal"]


class CrtSignal(TradebotSignal):
    STRATEGY_KEY = "crt"
