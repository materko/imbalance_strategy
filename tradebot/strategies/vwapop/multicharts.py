"""VWAP OP v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/VwapOp_Signal.py`.
HTF sviečky (VWAP aj drift) sa skladajú z barov grafu, takže na grafe stačí Data1 —
so skutočným objemom burzy (CME futures), inak je VWAP len odhad.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VwapOpSignal"]


class VwapOpSignal(TradebotSignal):
    STRATEGY_KEY = "vwapop"
