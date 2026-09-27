"""Liquidity v MultiCharts — študia nad generickým `TradebotSignal`.

Šablóna pre PowerLanguage .NET Editor: `deploy/multicharts/Liquidity_Signal.py`.
TF likvidity sa skladajú z barov grafu, takže na grafe stačí Data1.
"""

from __future__ import annotations

from tradebot.adapters.multicharts.signal import TradebotSignal

__all__ = ["LiquiditySignal"]


class LiquiditySignal(TradebotSignal):
    STRATEGY_KEY = "liquidity"
