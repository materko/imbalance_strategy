"""NB v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna: `deploy/multicharts/Nb_Signal.py`. Na grafe stačí Data1 (vyšší TF sa skladá zo sviečok grafu).
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["NbSignal"]


class NbSignal(TradebotSignal):
    STRATEGY_KEY = "nb"
