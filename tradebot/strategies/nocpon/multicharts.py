"""NOC + PONDELOK v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/NocPon_Signal.py`. Na grafe stačí Data1 (5m).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NocPonSignal"]


class NocPonSignal(TradebotSignal):
    STRATEGY_KEY = "nocpon"
