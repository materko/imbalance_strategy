"""VA NÁVRAT 1.0 v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Va80_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["Va80Signal"]


class Va80Signal(TradebotSignal):
    STRATEGY_KEY = "va80"
