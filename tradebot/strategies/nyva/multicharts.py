"""NY VA BREAKOUT v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/NyVa_Signal.py`. Na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NyVaSignal"]


class NyVaSignal(TradebotSignal):
    STRATEGY_KEY = "nyva"
