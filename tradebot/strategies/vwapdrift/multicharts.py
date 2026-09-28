"""Drift VWAP v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/VwapDrift_Signal.py`.
15m sviečky VWAP sa skladajú z barov grafu, takže na grafe stačí Data1 — so skutočným
objemom burzy (CME futures), inak je VWAP len odhad.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VwapDriftSignal"]


class VwapDriftSignal(TradebotSignal):
    STRATEGY_KEY = "vwapdrift"
