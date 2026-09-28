"""VWAP ORB v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/VwapOrb_Signal.py`.
Na grafe stačí Data1 so skutočným objemom burzy (CME futures), inak je VWAP len odhad.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["VwapOrbSignal"]


class VwapOrbSignal(TradebotSignal):
    STRATEGY_KEY = "vwaporb"
